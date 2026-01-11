#!/usr/bin/env python3
"""
Web Interface for Certificate of Origin Generator
Flask-based web application for uploading Bill of Lading and Invoice, generating certificates
Uses Word template with seals and signatures for professional output
API key loaded from .env file, model selection is automatic with fallback
"""

from flask import Flask, render_template, request, send_file, jsonify
import os
import tempfile
import zipfile
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from word_generator import WordCertificateGenerator, GeminiExtractor as WordGeminiExtractor
from word_generator import BuyerInfo, SellerInfo, ProductInfo, ShippingInfo, InvoiceInfo, CertificateData
import json

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Template path (Word document with seals and signatures)
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'template.docx')

# API key from environment (optional in form if set in .env)
API_KEY = os.environ.get('GEMINI_API_KEY', '')

def get_api_key(form_key=None):
    """Get API key from form or environment"""
    if form_key and form_key.strip():
        return form_key.strip()
    if API_KEY and API_KEY != 'your_api_key_here':
        return API_KEY
    return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate_certificate():
    """Generate certificate from uploaded Bill of Lading using Word template"""
    try:
        api_key = get_api_key(request.form.get('api_key'))
        if not api_key:
            return jsonify({'error': 'API key is required. Set GEMINI_API_KEY in .env file or provide in form.'}), 400
        
        if 'bill_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['bill_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_input = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_input)
        
        # Extract data using Gemini (model selection is automatic with fallback)
        extractor = WordGeminiExtractor(api_key)
        extracted_data = extractor.extract_from_bill(temp_input)
        
        if not extracted_data:
            os.remove(temp_input)
            return jsonify({'error': 'Failed to extract data from Bill of Lading'}), 400
        
        print("Extracted data:", json.dumps(extracted_data, indent=2))
        
        # Create data objects
        buyer = BuyerInfo(
            name=extracted_data.get('buyer', {}).get('name', ''),
            address=extracted_data.get('buyer', {}).get('address', ''),
            mobile=extracted_data.get('buyer', {}).get('mobile', ''),
            tax_number=extracted_data.get('buyer', {}).get('tax_number', ''),
            email=extracted_data.get('buyer', {}).get('email', '')
        )
        
        seller = SellerInfo(
            name=extracted_data.get('seller', {}).get('name', ''),
            address=extracted_data.get('seller', {}).get('address', '')
        )
        
        product = ProductInfo(
            description=extracted_data.get('product', {}).get('description', ''),
            hs_code=extracted_data.get('product', {}).get('hs_code', ''),
            quantity=extracted_data.get('product', {}).get('quantity', ''),
            weight=extracted_data.get('product', {}).get('weight', ''),
            marks_numbers=extracted_data.get('product', {}).get('marks_numbers', 'N/M')
        )
        
        shipping = ShippingInfo(
            port_of_loading=extracted_data.get('shipping', {}).get('port_of_loading', ''),
            port_of_discharge=extracted_data.get('shipping', {}).get('port_of_discharge', ''),
            destination_country=extracted_data.get('shipping', {}).get('destination_country', '')
        )
        
        invoice = InvoiceInfo(
            invoice_number=extracted_data.get('invoice', {}).get('invoice_number', ''),
            invoice_date=extracted_data.get('invoice', {}).get('invoice_date', '')
        )
        
        # Generate certificate using Word template
        generator = WordCertificateGenerator(TEMPLATE_PATH)
        serial_no, cert_no = generator.generate_certificate_number()
        declaration_date = generator.generate_declaration_date(invoice.invoice_date)
        
        cert_data = CertificateData(
            buyer=buyer,
            seller=seller,
            product=product,
            shipping=shipping,
            invoice=invoice,
            serial_number=serial_no,
            certificate_number=cert_no,
            declaration_date=declaration_date
        )
        
        # Generate output
        temp_docx = os.path.join(app.config['UPLOAD_FOLDER'], 'certificate_output.docx')
        docx_path, pdf_path = generator.create_certificate(cert_data, temp_docx, output_pdf=True)
        
        # Clean up input file
        os.remove(temp_input)
        
        # Create ZIP file with both Word and PDF
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'certificate_of_origin.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if docx_path and os.path.exists(docx_path):
                zipf.write(docx_path, 'certificate_of_origin.docx')
            if pdf_path and os.path.exists(pdf_path):
                zipf.write(pdf_path, 'certificate_of_origin.pdf')
        
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name='certificate_of_origin.zip'
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/generate-combined', methods=['POST'])
def generate_combined():
    """Generate certificate from both Invoice and Bill of Lading using Word template"""
    try:
        api_key = get_api_key(request.form.get('api_key'))
        if not api_key:
            return jsonify({'error': 'API key is required. Set GEMINI_API_KEY in .env file or provide in form.'}), 400
        
        invoice_file = request.files.get('invoice_file')
        bill_file = request.files.get('bill_file')
        
        if not invoice_file and not bill_file:
            return jsonify({'error': 'At least one file (Invoice or Bill) is required'}), 400
        
        # Save uploaded files temporarily
        temp_invoice = None
        temp_bill = None
        
        if invoice_file and invoice_file.filename:
            filename = secure_filename(invoice_file.filename)
            temp_invoice = os.path.join(app.config['UPLOAD_FOLDER'], f'invoice_{filename}')
            invoice_file.save(temp_invoice)
        
        if bill_file and bill_file.filename:
            filename = secure_filename(bill_file.filename)
            temp_bill = os.path.join(app.config['UPLOAD_FOLDER'], f'bill_{filename}')
            bill_file.save(temp_bill)
        
        # Extract data from each document separately
        extractor = WordGeminiExtractor(api_key)
        
        bill_data = {}
        invoice_data = {}
        
        # Extract from Bill of Lading first (primary source for buyer, seller, product, shipping)
        if temp_bill:
            print(f"Extracting from Bill of Lading: {temp_bill}")
            bill_data = extractor.extract_from_bill(temp_bill)
            print(f"Bill data: {json.dumps(bill_data, indent=2)}")
        
        # Extract from Invoice (only for invoice number and date)
        if temp_invoice:
            print(f"Extracting from Invoice: {temp_invoice}")
            invoice_data = extractor.extract_from_bill(temp_invoice)
            print(f"Invoice data: {json.dumps(invoice_data, indent=2)}")
        
        # Merge data: Bill of Lading is primary, Invoice provides invoice info + contact details
        if bill_data:
            extracted_data = bill_data.copy()
            # Take invoice number and date from invoice document
            if invoice_data and invoice_data.get('invoice'):
                if not extracted_data.get('invoice'):
                    extracted_data['invoice'] = {}
                if invoice_data['invoice'].get('invoice_number'):
                    extracted_data['invoice']['invoice_number'] = invoice_data['invoice']['invoice_number']
                if invoice_data['invoice'].get('invoice_date'):
                    extracted_data['invoice']['invoice_date'] = invoice_data['invoice']['invoice_date']
            # Also take buyer name, mobile, tax_number, email from invoice
            if invoice_data and invoice_data.get('buyer'):
                if not extracted_data.get('buyer'):
                    extracted_data['buyer'] = {}
                if invoice_data['buyer'].get('name'):
                    extracted_data['buyer']['name'] = invoice_data['buyer']['name']
                if invoice_data['buyer'].get('mobile'):
                    extracted_data['buyer']['mobile'] = invoice_data['buyer']['mobile']
                if invoice_data['buyer'].get('tax_number'):
                    extracted_data['buyer']['tax_number'] = invoice_data['buyer']['tax_number']
                if invoice_data['buyer'].get('email'):
                    extracted_data['buyer']['email'] = invoice_data['buyer']['email']
            
            # Take seller name from invoice
            if invoice_data and invoice_data.get('seller'):
                if not extracted_data.get('seller'):
                    extracted_data['seller'] = {}
                if invoice_data['seller'].get('name'):
                    extracted_data['seller']['name'] = invoice_data['seller']['name']
        elif invoice_data:
            extracted_data = invoice_data
        else:
            extracted_data = {}
        
        # Clean up input files
        if temp_invoice and os.path.exists(temp_invoice):
            os.remove(temp_invoice)
        if temp_bill and os.path.exists(temp_bill):
            os.remove(temp_bill)
        
        if not extracted_data:
            return jsonify({'error': 'Failed to extract data from documents'}), 400
        
        print("Final merged data:", json.dumps(extracted_data, indent=2))
        
        # Create data objects
        buyer = BuyerInfo(
            name=extracted_data.get('buyer', {}).get('name', ''),
            address=extracted_data.get('buyer', {}).get('address', ''),
            mobile=extracted_data.get('buyer', {}).get('mobile', ''),
            tax_number=extracted_data.get('buyer', {}).get('tax_number', ''),
            email=extracted_data.get('buyer', {}).get('email', '')
        )
        
        seller = SellerInfo(
            name=extracted_data.get('seller', {}).get('name', ''),
            address=extracted_data.get('seller', {}).get('address', '')
        )
        
        product = ProductInfo(
            description=extracted_data.get('product', {}).get('description', ''),
            hs_code=extracted_data.get('product', {}).get('hs_code', ''),
            quantity=extracted_data.get('product', {}).get('quantity', ''),
            weight=extracted_data.get('product', {}).get('weight', ''),
            marks_numbers=extracted_data.get('product', {}).get('marks_numbers', 'N/M')
        )
        
        shipping = ShippingInfo(
            port_of_loading=extracted_data.get('shipping', {}).get('port_of_loading', ''),
            port_of_discharge=extracted_data.get('shipping', {}).get('port_of_discharge', ''),
            destination_country=extracted_data.get('shipping', {}).get('destination_country', '')
        )
        
        invoice = InvoiceInfo(
            invoice_number=extracted_data.get('invoice', {}).get('invoice_number', ''),
            invoice_date=extracted_data.get('invoice', {}).get('invoice_date', '')
        )
        
        # Generate certificate using Word template
        generator = WordCertificateGenerator(TEMPLATE_PATH)
        serial_no, cert_no = generator.generate_certificate_number()
        declaration_date = generator.generate_declaration_date(invoice.invoice_date)
        
        cert_data = CertificateData(
            buyer=buyer,
            seller=seller,
            product=product,
            shipping=shipping,
            invoice=invoice,
            serial_number=serial_no,
            certificate_number=cert_no,
            declaration_date=declaration_date
        )
        
        # Generate output
        temp_docx = os.path.join(app.config['UPLOAD_FOLDER'], 'certificate_combined.docx')
        docx_path, pdf_path = generator.create_certificate(cert_data, temp_docx, output_pdf=True)
        
        # Create ZIP file with both Word and PDF
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'certificate_of_origin.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if docx_path and os.path.exists(docx_path):
                zipf.write(docx_path, 'certificate_of_origin.docx')
            if pdf_path and os.path.exists(pdf_path):
                zipf.write(pdf_path, 'certificate_of_origin.pdf')
        
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name='certificate_of_origin.zip'
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/generate-manual', methods=['POST'])
def generate_manual():
    """Generate certificate from manual form data using Word template"""
    try:
        # Get form data
        buyer = BuyerInfo(
            name=request.form.get('buyer_name', ''),
            address=request.form.get('buyer_address', ''),
            mobile=request.form.get('buyer_mobile', ''),
            tax_number=request.form.get('buyer_tax', ''),
            email=request.form.get('buyer_email', '')
        )
        
        seller = SellerInfo(
            name=request.form.get('seller_name', ''),
            address=request.form.get('seller_address', '')
        )
        
        product = ProductInfo(
            description=request.form.get('product_description', ''),
            hs_code=request.form.get('hs_code', ''),
            quantity=request.form.get('quantity', ''),
            weight=request.form.get('weight', ''),
            marks_numbers=request.form.get('marks_numbers', 'N/M')
        )
        
        shipping = ShippingInfo(
            port_of_loading=request.form.get('port_loading', ''),
            port_of_discharge=request.form.get('port_discharge', ''),
            destination_country=request.form.get('destination', '')
        )
        
        # Format invoice date
        invoice_date = request.form.get('invoice_date', '')
        if invoice_date:
            from datetime import datetime
            dt = datetime.strptime(invoice_date, '%Y-%m-%d')
            invoice_date = dt.strftime('%b.%d,%Y').upper()
        
        invoice = InvoiceInfo(
            invoice_number=request.form.get('invoice_number', ''),
            invoice_date=invoice_date
        )
        
        # Generate certificate using Word template
        generator = WordCertificateGenerator(TEMPLATE_PATH)
        serial_no, cert_no = generator.generate_certificate_number()
        declaration_date = generator.generate_declaration_date(invoice_date)
        
        cert_data = CertificateData(
            buyer=buyer,
            seller=seller,
            product=product,
            shipping=shipping,
            invoice=invoice,
            serial_number=serial_no,
            certificate_number=cert_no,
            declaration_date=declaration_date
        )
        
        # Generate output
        temp_docx = os.path.join(app.config['UPLOAD_FOLDER'], 'certificate_manual.docx')
        docx_path, pdf_path = generator.create_certificate(cert_data, temp_docx, output_pdf=True)
        
        # Create ZIP file with both Word and PDF
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'certificate_of_origin.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if docx_path and os.path.exists(docx_path):
                zipf.write(docx_path, 'certificate_of_origin.docx')
            if pdf_path and os.path.exists(pdf_path):
                zipf.write(pdf_path, 'certificate_of_origin.pdf')
        
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name='certificate_of_origin.zip'
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
