#!/usr/bin/env python3
"""
Certificate of Origin Generator - Template Based Version
Uses the original certificate PDF as template and overlays new data
Preserves blue colors, seals, stamps, and signatures
"""

import os
import io
import json
import random
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
import re

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import white, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import pdfplumber

# For Gemini API - try newer package first, fall back to older
try:
    from google import genai
    USE_NEW_GENAI = True
except ImportError:
    import google.generativeai as genai
    USE_NEW_GENAI = False


@dataclass
class BuyerInfo:
    """Buyer/Consignee information"""
    name: str
    address: str
    mobile: str = ""
    tax_number: str = ""
    email: str = ""


@dataclass
class SellerInfo:
    """Seller/Exporter information"""
    name: str
    address: str


@dataclass
class ProductInfo:
    """Product details"""
    description: str
    hs_code: str
    quantity: str
    weight: str
    marks_numbers: str = "N/M"


@dataclass
class ShippingInfo:
    """Shipping route information"""
    port_of_loading: str
    port_of_discharge: str
    destination_country: str


@dataclass
class InvoiceInfo:
    """Invoice details"""
    invoice_number: str
    invoice_date: str  # Format: "MMM.DD,YYYY" like "OCT.09,2025"


@dataclass
class CertificateData:
    """Complete certificate data"""
    buyer: BuyerInfo
    seller: SellerInfo
    product: ProductInfo
    shipping: ShippingInfo
    invoice: InvoiceInfo
    certificate_number: str = ""
    serial_number: str = ""
    declaration_date: str = ""


class GeminiExtractor:
    """Extract data from Bill of Lading using Google Gemini API"""
    
    def __init__(self, api_key: str):
        """Initialize Gemini API"""
        if USE_NEW_GENAI:
            self.client = genai.Client(api_key=api_key)
            self.model_name = 'gemini-1.5-flash'
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.api_key = api_key
    
    def extract_from_bill(self, pdf_path: str) -> dict:
        """Extract all relevant information from Bill of Lading PDF"""
        text_content = self._extract_pdf_text(pdf_path)
        
        if not text_content.strip():
            print("PDF appears to be image-based, using Gemini Vision...")
            return self._extract_from_pdf_image(pdf_path)
        
        return self._extract_from_text(text_content)
    
    def _extract_from_text(self, text_content: str) -> dict:
        """Extract data from text content using Gemini"""
        prompt = self._get_extraction_prompt(f"Bill of Lading Content:\n{text_content}")
        
        if USE_NEW_GENAI:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
        else:
            response = self.model.generate_content(prompt)
        
        return self._parse_response(response)
    
    def _extract_from_pdf_image(self, pdf_path: str) -> dict:
        """Extract data from PDF by converting to image and using Gemini Vision"""
        import subprocess
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_prefix = os.path.join(tmpdir, "page")
            
            try:
                subprocess.run([
                    'pdftoppm', '-png', '-r', '200',
                    pdf_path, output_prefix
                ], check=True, capture_output=True)
            except FileNotFoundError:
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(pdf_path, dpi=200)
                    for i, img in enumerate(images):
                        img.save(os.path.join(tmpdir, f"page-{i+1}.png"), 'PNG')
                except ImportError:
                    print("Warning: pdftoppm not available and pdf2image not installed")
                    return {}
            
            image_files = sorted(Path(tmpdir).glob("page*.png"))
            
            if not image_files:
                print("No images generated from PDF")
                return {}
            
            image_path = str(image_files[0])
            
            import PIL.Image
            image = PIL.Image.open(image_path)
            
            prompt = self._get_extraction_prompt("Please analyze this Bill of Lading image and extract the information.")
            
            if USE_NEW_GENAI:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt, image]
                )
            else:
                response = self.model.generate_content([prompt, image])
            
            return self._parse_response(response)
    
    def _get_extraction_prompt(self, context: str) -> str:
        """Get the standard extraction prompt"""
        return f"""
You are an expert at extracting information from shipping documents (Bill of Lading).

Extract the following information and return it as a valid JSON object:

{{
    "buyer": {{
        "name": "Company name of the consignee/buyer (CONSIGNEE field)",
        "address": "Full address of the consignee",
        "mobile": "Mobile/phone numbers if available",
        "tax_number": "Tax number if available",
        "email": "Email if available"
    }},
    "seller": {{
        "name": "Company name of the shipper/exporter (SHIPPER field)",
        "address": "Full address of the shipper"
    }},
    "product": {{
        "description": "Description of goods (e.g., 'SIX HUNDRED FORTY (640) CTNS OF GLASS ELECTRIC KETTLE')",
        "hs_code": "HS/Harmonized Code with decimal (e.g., '851671.00')",
        "quantity": "Number of items/cartons (e.g., '640')",
        "weight": "Gross weight with unit (e.g., '7,910 KGS G.W.' or '7,910.000 kgs')",
        "marks_numbers": "Container number or marks, otherwise 'N/M'"
    }},
    "shipping": {{
        "port_of_loading": "Port of loading (e.g., 'SHEKOU CHINA' or 'NINGBO CHINA')",
        "port_of_discharge": "Port of discharge (e.g., 'UMM QASR PT, IRAQ')",
        "destination_country": "Destination country (e.g., 'IRAQ')"
    }},
    "invoice": {{
        "invoice_number": "Invoice/reference/booking number",
        "invoice_date": "Date found on document, convert to format MMM.DD,YYYY (e.g., 'OCT.30,2025')"
    }}
}}

Important:
- Return ONLY the JSON object, no markdown formatting, no explanation
- If information is not found, use empty string ""
- For dates, convert to format like "OCT.09,2025" (uppercase month abbreviation)
- For HS code, include decimal like "851671.00"

{context}
"""
    
    def _parse_response(self, response) -> dict:
        """Parse Gemini response into dictionary"""
        try:
            response_text = response.text.strip()
            if response_text.startswith("```"):
                response_text = re.sub(r'^```json?\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)
            
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Error parsing Gemini response: {e}")
            print(f"Response was: {response.text}")
            return {}
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF using pdfplumber"""
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text


class TemplateBasedGenerator:
    """
    Generate Certificate of Origin by overlaying data on original template PDF
    Preserves the blue colors, seals, stamps, and signatures
    """
    
    def __init__(self, template_path: str):
        """
        Initialize with path to template PDF
        
        Args:
            template_path: Path to the original certificate PDF to use as template
        """
        self.template_path = template_path
        self.page_width = 595.56  # A4 width in points
        self.page_height = 842.04  # A4 height in points
        
        # Define field positions (x, y from top-left, width, height) in points
        # These are areas where we need to clear old text and write new text
        self.fields = {
            # Section 1: Exporter
            'exporter_name': {'x': 47, 'y': 47, 'w': 250, 'h': 10, 'font_size': 8},
            'exporter_address': {'x': 47, 'y': 55, 'w': 250, 'h': 20, 'font_size': 7},
            
            # Serial and Certificate numbers
            'serial_no': {'x': 356, 'y': 40, 'w': 120, 'h': 10, 'font_size': 8},
            'cert_no': {'x': 354, 'y': 53, 'w': 120, 'h': 10, 'font_size': 8},
            
            # Section 2: Consignee
            'consignee_name': {'x': 47, 'y': 95, 'w': 250, 'h': 30, 'font_size': 7},
            'consignee_address': {'x': 47, 'y': 125, 'w': 250, 'h': 25, 'font_size': 7},
            
            # Section 3: Transport
            'transport': {'x': 47, 'y': 175, 'w': 250, 'h': 10, 'font_size': 8},
            
            # Section 4: Destination
            'destination': {'x': 47, 'y': 212, 'w': 100, 'h': 10, 'font_size': 8},
            
            # Section 6: Marks and numbers
            'marks': {'x': 30, 'y': 275, 'w': 55, 'h': 12, 'font_size': 8},
            
            # Section 7: Description of goods
            'goods_desc': {'x': 115, 'y': 275, 'w': 165, 'h': 60, 'font_size': 8},
            
            # Section 8: HS Code
            'hs_code': {'x': 400, 'y': 275, 'w': 50, 'h': 12, 'font_size': 8},
            
            # Section 9: Quantity/Weight
            'weight': {'x': 455, 'y': 275, 'w': 50, 'h': 20, 'font_size': 7},
            
            # Section 10: Invoice
            'invoice_no': {'x': 508, 'y': 275, 'w': 55, 'h': 12, 'font_size': 7},
            'invoice_date': {'x': 508, 'y': 295, 'w': 55, 'h': 12, 'font_size': 7},
            
            # Section 11: Declaration date
            'declaration_date_11': {'x': 47, 'y': 745, 'w': 120, 'h': 12, 'font_size': 8},
            
            # Section 12: Certification date
            'declaration_date_12': {'x': 330, 'y': 745, 'w': 120, 'h': 12, 'font_size': 8},
        }
    
    def generate_declaration_date(self, invoice_date_str: str) -> str:
        """Generate declaration date 10-30 days after invoice date"""
        try:
            invoice_date = datetime.strptime(invoice_date_str, "%b.%d,%Y")
        except ValueError:
            try:
                invoice_date = datetime.strptime(invoice_date_str, "%d-%b-%Y")
            except ValueError:
                invoice_date = datetime.now()
        
        random_days = random.randint(10, 30)
        declaration_date = invoice_date + timedelta(days=random_days)
        return declaration_date.strftime("%b.%d,%Y").upper()
    
    def generate_certificate_number(self) -> tuple:
        """Generate certificate and serial numbers"""
        serial = f"CCPIT351250{random.randint(100000, 999999)}"
        cert = f"25C35112{random.randint(1000, 9999)}/000{random.randint(10, 99)}"
        return serial, cert
    
    def create_certificate(self, data: CertificateData, output_path: str):
        """
        Create certificate by overlaying data on template
        
        Args:
            data: CertificateData with all the information to fill in
            output_path: Where to save the generated certificate
        """
        # Read the template
        template_reader = PdfReader(self.template_path)
        template_page = template_reader.pages[0]
        
        # Create overlay with new data
        overlay_buffer = io.BytesIO()
        c = canvas.Canvas(overlay_buffer, pagesize=(self.page_width, self.page_height))
        
        # Draw white rectangles to cover old text, then draw new text
        self._draw_all_fields(c, data)
        
        c.save()
        overlay_buffer.seek(0)
        
        # Merge overlay with template
        overlay_reader = PdfReader(overlay_buffer)
        overlay_page = overlay_reader.pages[0]
        
        template_page.merge_page(overlay_page)
        
        # Write output
        writer = PdfWriter()
        writer.add_page(template_page)
        
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        print(f"Certificate generated: {output_path}")
    
    def _draw_all_fields(self, c, data: CertificateData):
        """Draw all fields on the overlay canvas"""
        
        # Helper to convert y from top to bottom (PDF coordinates)
        def y_from_top(y_top):
            return self.page_height - y_top
        
        # Section 1: Exporter
        self._clear_and_write(c, 47, y_from_top(47), 250, 8,
                             data.seller.name, 8)
        
        # Exporter address (multi-line)
        address_lines = self._wrap_text(data.seller.address + " ***", 70)
        y_addr = y_from_top(55)
        for line in address_lines:
            c.setFont("Helvetica", 7)
            c.drawString(47, y_addr, line)
            y_addr -= 8
        
        # Serial and Certificate numbers
        self._clear_and_write(c, 356, y_from_top(40), 120, 10,
                             data.serial_number, 8)
        self._clear_and_write(c, 354, y_from_top(53), 120, 10,
                             data.certificate_number, 8)
        
        # Section 2: Consignee name (multi-line)
        consignee_lines = self._wrap_text(data.buyer.name, 65)
        y_cons = y_from_top(95)
        c.setFillColor(white)
        c.rect(47, y_from_top(130), 250, 40, fill=True, stroke=False)
        c.setFillColor(black)
        for line in consignee_lines:
            c.setFont("Helvetica", 7)
            c.drawString(47, y_cons, line)
            y_cons -= 9
        
        # Consignee address
        addr_text = f"ADDRESS : {data.buyer.address}"
        addr_lines = self._wrap_text(addr_text, 65)
        for line in addr_lines:
            c.setFont("Helvetica", 7)
            c.drawString(47, y_cons, line)
            y_cons -= 9
        
        # Section 3: Transport route
        transport_text = f"FROM {data.shipping.port_of_loading} TO {data.shipping.port_of_discharge} BY SEA"
        self._clear_and_write(c, 47, y_from_top(175), 250, 10,
                             transport_text, 8)
        
        # Section 4: Destination
        self._clear_and_write(c, 47, y_from_top(212), 100, 10,
                             data.shipping.destination_country, 8)
        
        # Section 6: Marks and numbers
        self._clear_and_write(c, 30, y_from_top(280), 55, 12,
                             data.product.marks_numbers, 8)
        
        # Section 7: Goods description with buyer contact info
        c.setFillColor(white)
        c.rect(115, y_from_top(340), 165, 70, fill=True, stroke=False)
        c.setFillColor(black)
        
        # Product description
        desc_lines = self._wrap_text(data.product.description, 45)
        y_goods = y_from_top(280)
        for line in desc_lines:
            c.setFont("Helvetica", 8)
            c.drawString(115, y_goods, line)
            y_goods -= 10
        
        # Add buyer contact info
        y_goods -= 5
        if data.buyer.mobile:
            c.setFont("Helvetica", 7)
            c.drawString(115, y_goods, f"**MOBILE NUMBER : {data.buyer.mobile}")
            y_goods -= 9
        
        if data.buyer.tax_number:
            c.setFont("Helvetica", 7)
            c.drawString(115, y_goods, f"TAX NUMBER : {data.buyer.tax_number}")
            y_goods -= 9
        
        if data.buyer.email:
            c.setFont("Helvetica", 7)
            c.drawString(115, y_goods, f"EMAIL : {data.buyer.email}")
            y_goods -= 9
        
        c.drawString(115, y_goods, "***")
        
        # Section 8: HS Code
        self._clear_and_write(c, 400, y_from_top(280), 50, 12,
                             data.product.hs_code, 8)
        
        # Section 9: Weight
        c.setFillColor(white)
        c.rect(455, y_from_top(295), 50, 25, fill=True, stroke=False)
        c.setFillColor(black)
        c.setFont("Helvetica", 7)
        c.drawString(455, y_from_top(280), "G.WEIGHT")
        c.drawString(455, y_from_top(290), data.product.weight)
        
        # Section 10: Invoice
        c.setFillColor(white)
        c.rect(508, y_from_top(310), 60, 40, fill=True, stroke=False)
        c.setFillColor(black)
        
        # Invoice number (may need to be split if too long)
        inv_no = data.invoice.invoice_number
        if len(inv_no) > 12:
            # Split into two lines
            c.setFont("Helvetica", 6)
            c.drawString(508, y_from_top(280), inv_no[:12])
            c.drawString(508, y_from_top(288), inv_no[12:])
        else:
            c.setFont("Helvetica", 7)
            c.drawString(508, y_from_top(280), inv_no)
        
        c.setFont("Helvetica", 7)
        c.drawString(508, y_from_top(300), data.invoice.invoice_date)
        
        # Section 11 & 12: Declaration dates
        date_text = f"YIWU,CHINA {data.declaration_date}"
        
        # Clear and write date in section 11
        c.setFillColor(white)
        c.rect(47, y_from_top(752), 130, 12, fill=True, stroke=False)
        c.setFillColor(black)
        c.setFont("Helvetica", 8)
        c.drawString(47, y_from_top(745), date_text)
        
        # Clear and write date in section 12
        c.setFillColor(white)
        c.rect(330, y_from_top(752), 130, 12, fill=True, stroke=False)
        c.setFillColor(black)
        c.setFont("Helvetica", 8)
        c.drawString(330, y_from_top(745), date_text)
    
    def _clear_and_write(self, c, x, y, w, h, text, font_size):
        """Clear area with white rectangle and write new text"""
        c.setFillColor(white)
        c.rect(x, y - h + font_size, w, h, fill=True, stroke=False)
        c.setFillColor(black)
        c.setFont("Helvetica", font_size)
        c.drawString(x, y, text)
    
    def _wrap_text(self, text: str, max_chars: int) -> list:
        """Wrap text to fit within max characters per line"""
        lines = []
        for paragraph in text.split('\n'):
            words = paragraph.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= max_chars:
                    current_line += (" " if current_line else "") + word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
        return lines


def process_bill_of_lading(bill_pdf_path: str, api_key: str, template_path: str, output_path: str = None):
    """
    Main function to process a Bill of Lading and generate Certificate of Origin
    
    Args:
        bill_pdf_path: Path to the Bill of Lading PDF
        api_key: Google Gemini API key
        template_path: Path to the certificate template PDF
        output_path: Output path for the certificate (optional)
    
    Returns:
        Path to generated certificate PDF
    """
    
    # Initialize extractor
    extractor = GeminiExtractor(api_key)
    
    # Extract data from bill
    print(f"Extracting data from: {bill_pdf_path}")
    extracted_data = extractor.extract_from_bill(bill_pdf_path)
    
    if not extracted_data:
        raise ValueError("Failed to extract data from Bill of Lading")
    
    print("Extracted data:")
    print(json.dumps(extracted_data, indent=2))
    
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
    
    # Generate certificate
    generator = TemplateBasedGenerator(template_path)
    
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
    
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"certificate_of_origin_{timestamp}.pdf"
    
    generator.create_certificate(cert_data, output_path)
    
    return output_path


def main():
    """Command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Certificate of Origin from Bill of Lading')
    parser.add_argument('bill_pdf', help='Path to Bill of Lading PDF')
    parser.add_argument('--api-key', required=True, help='Google Gemini API key')
    parser.add_argument('--template', '-t', required=True, help='Path to certificate template PDF')
    parser.add_argument('--output', '-o', help='Output PDF path')
    
    args = parser.parse_args()
    
    output_path = process_bill_of_lading(
        args.bill_pdf,
        args.api_key,
        args.template,
        args.output
    )
    
    print(f"\nCertificate generated successfully: {output_path}")


if __name__ == "__main__":
    main()
