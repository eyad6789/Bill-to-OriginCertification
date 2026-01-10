#!/usr/bin/env python3
"""
Certificate of Origin Generator System
Extracts data from Bill of Lading PDF and generates Certificate of Origin PDF
Uses Google Gemini API for intelligent data extraction
"""

import os
import json
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional
import re

# PDF processing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# For Gemini API - try newer package first, fall back to older
try:
    from google import genai
    USE_NEW_GENAI = True
except ImportError:
    import google.generativeai as genai
    USE_NEW_GENAI = False

# For PDF text extraction
import pdfplumber


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
    declaration_date: str = ""  # Will be auto-generated


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
        
        # First try to extract text from PDF
        text_content = self._extract_pdf_text(pdf_path)
        
        # If no text found, PDF is likely image-based - use vision
        if not text_content.strip():
            print("PDF appears to be image-based, using Gemini Vision...")
            return self._extract_from_pdf_image(pdf_path)
        
        # Use Gemini to parse and extract structured data from text
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
        import base64
        from pathlib import Path
        
        # Convert PDF to image using pdftoppm
        with tempfile.TemporaryDirectory() as tmpdir:
            output_prefix = os.path.join(tmpdir, "page")
            
            # Use pdftoppm to convert PDF to PNG
            try:
                subprocess.run([
                    'pdftoppm', '-png', '-r', '200',
                    pdf_path, output_prefix
                ], check=True, capture_output=True)
            except FileNotFoundError:
                # Try alternative: convert using pdf2image if available
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(pdf_path, dpi=200)
                    for i, img in enumerate(images):
                        img.save(os.path.join(tmpdir, f"page-{i+1}.png"), 'PNG')
                except ImportError:
                    print("Warning: pdftoppm not available and pdf2image not installed")
                    return {}
            
            # Find generated images
            image_files = sorted(Path(tmpdir).glob("page*.png"))
            
            if not image_files:
                print("No images generated from PDF")
                return {}
            
            # Read the first page image (usually Bill of Lading is single page)
            image_path = str(image_files[0])
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Use Gemini Vision to extract data
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
        "invoice_number": "Invoice/reference/booking number (look for REF, BOOKING REF, or similar)",
        "invoice_date": "Date found on document, convert to format MMM.DD,YYYY (e.g., 'OCT.30,2025')"
    }}
}}

Important:
- Return ONLY the JSON object, no markdown formatting, no explanation
- If information is not found, use empty string ""
- For dates, convert to format like "OCT.09,2025" (uppercase month abbreviation)
- For HS code, include decimal like "851671.00"
- Look for SHIPPER for seller, CONSIGNEE for buyer
- PORT OF LOADING for origin, PORT OF DISCHARGE for destination

{context}
"""
    
    def _parse_response(self, response) -> dict:
        """Parse Gemini response into dictionary"""
        try:
            response_text = response.text.strip()
            # Remove markdown code blocks if present
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


class CertificateGenerator:
    """Generate Certificate of Origin PDF"""
    
    def __init__(self):
        self.page_width, self.page_height = A4
    
    def generate_declaration_date(self, invoice_date_str: str) -> str:
        """
        Generate declaration date based on invoice date
        Random date between 10 days and 1 month after invoice date
        Format: "MMM.DD,YYYY" (e.g., "NOV.25,2025")
        """
        # Parse invoice date
        try:
            # Try parsing "OCT.09,2025" format
            invoice_date = datetime.strptime(invoice_date_str, "%b.%d,%Y")
        except ValueError:
            try:
                # Try "30-Oct-2025" format
                invoice_date = datetime.strptime(invoice_date_str, "%d-%b-%Y")
            except ValueError:
                # Default to current date if parsing fails
                invoice_date = datetime.now()
        
        # Generate random days between 10 and 30 (max 1 month)
        random_days = random.randint(10, 30)
        declaration_date = invoice_date + timedelta(days=random_days)
        
        # Format as "NOV.25,2025"
        return declaration_date.strftime("%b.%d,%Y").upper()
    
    def generate_certificate_number(self) -> tuple:
        """Generate certificate and serial numbers"""
        # Generate random numbers similar to the template
        serial = f"CCPIT351250{random.randint(100000, 999999)}"
        cert = f"25C35112{random.randint(1000, 9999)}/000{random.randint(10, 99)}"
        return serial, cert
    
    def create_certificate(self, data: CertificateData, output_path: str):
        """Create the Certificate of Origin PDF"""
        
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4
        
        # Set up fonts
        c.setFont("Helvetica-Bold", 16)
        
        # Header - ORIGINAL
        c.drawCentredString(width/2, height - 30*mm, "ORIGINAL")
        
        # Certificate numbers (top right)
        c.setFont("Helvetica", 9)
        c.drawString(120*mm, height - 15*mm, f"Serial No. {data.serial_number}")
        c.drawString(120*mm, height - 20*mm, f"Certificate No. {data.certificate_number}")
        
        # Title
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(160*mm, height - 35*mm, "CERTIFICATE OF ORIGIN")
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(160*mm, height - 42*mm, "OF")
        c.drawCentredString(160*mm, height - 49*mm, "THE PEOPLE'S REPUBLIC OF CHINA")
        
        # Draw boxes and content
        self._draw_exporter_box(c, data.seller, height)
        self._draw_consignee_box(c, data.buyer, height)
        self._draw_transport_box(c, data.shipping, height)
        self._draw_destination_box(c, data.shipping, height)
        self._draw_certifying_authority_box(c, height)
        self._draw_goods_table(c, data, height)
        self._draw_declaration_box(c, data, height)
        self._draw_certification_box(c, data, height)
        
        c.save()
        print(f"Certificate generated: {output_path}")
    
    def _draw_exporter_box(self, c, seller: SellerInfo, height):
        """Draw exporter section"""
        y = height - 55*mm
        c.setFont("Helvetica-Bold", 8)
        c.drawString(10*mm, y, "1.Exporter")
        c.setFont("Helvetica", 8)
        
        # Split address into lines
        lines = self._wrap_text(f"{seller.name}\n{seller.address}", 60)
        y_text = y - 5*mm
        for line in lines:
            c.drawString(10*mm, y_text, line)
            y_text -= 4*mm
        
        # Draw box
        c.rect(8*mm, height - 85*mm, 100*mm, 35*mm)
    
    def _draw_consignee_box(self, c, buyer: BuyerInfo, height):
        """Draw consignee section"""
        y = height - 90*mm
        c.setFont("Helvetica-Bold", 8)
        c.drawString(10*mm, y, "2.Consignee")
        c.setFont("Helvetica", 7)
        
        # Build consignee text
        text = f"{buyer.name}\n{buyer.address}"
        if buyer.mobile:
            text += f"\n**MOBILE NUMBER : {buyer.mobile}"
        if buyer.tax_number:
            text += f"\nTAX NUMBER : {buyer.tax_number}"
        
        lines = self._wrap_text(text, 65)
        y_text = y - 5*mm
        for line in lines:
            c.drawString(10*mm, y_text, line)
            y_text -= 3.5*mm
        
        # Draw box
        c.rect(8*mm, height - 135*mm, 100*mm, 50*mm)
    
    def _draw_transport_box(self, c, shipping: ShippingInfo, height):
        """Draw transport section"""
        y = height - 140*mm
        c.setFont("Helvetica-Bold", 8)
        c.drawString(10*mm, y, "3.Means of transport and route")
        c.setFont("Helvetica", 8)
        c.drawString(10*mm, y - 5*mm, f"FROM {shipping.port_of_loading} TO {shipping.port_of_discharge} BY SEA")
        
        c.rect(8*mm, height - 155*mm, 100*mm, 20*mm)
    
    def _draw_destination_box(self, c, shipping: ShippingInfo, height):
        """Draw destination section"""
        y = height - 160*mm
        c.setFont("Helvetica-Bold", 8)
        c.drawString(10*mm, y, "4.Country / region of destination")
        c.setFont("Helvetica", 8)
        c.drawString(10*mm, y - 5*mm, shipping.destination_country)
        
        c.rect(8*mm, height - 175*mm, 100*mm, 20*mm)
    
    def _draw_certifying_authority_box(self, c, height):
        """Draw certifying authority section"""
        y = height - 90*mm
        x = 112*mm
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x, y, "5.For certifying authority use only")
        c.setFont("Helvetica", 7)
        c.drawString(x, y - 8*mm, "CHINA COUNCIL FOR THE")
        c.drawString(x, y - 12*mm, "PROMOTION OF INTERNATIONAL")
        c.drawString(x, y - 16*mm, "TRADE IS CHINA CHAMBER OF")
        c.drawString(x, y - 20*mm, "INTERNATIONAL COMMERCE")
        c.drawString(x, y - 28*mm, "VERIFY URL:HTTP://CHECK.ECOCCPIT.NET/")
        
        c.rect(110*mm, height - 135*mm, 92*mm, 50*mm)
    
    def _draw_goods_table(self, c, data: CertificateData, height):
        """Draw goods description table"""
        y = height - 180*mm
        
        # Headers
        c.setFont("Helvetica-Bold", 7)
        c.drawString(10*mm, y, "6.Marks and numbers")
        c.drawString(45*mm, y, "7.Number and kind of packages;description of goods")
        c.drawString(125*mm, y, "8.H.S.Code")
        c.drawString(145*mm, y, "9.Quantity")
        c.drawString(170*mm, y, "10.Number")
        c.drawString(170*mm, y - 4*mm, "and date of")
        c.drawString(170*mm, y - 8*mm, "invoices")
        
        # Content
        c.setFont("Helvetica", 8)
        y_content = y - 15*mm
        c.drawString(10*mm, y_content, data.product.marks_numbers)
        
        # Product description - wrap text
        desc_lines = self._wrap_text(data.product.description, 45)
        y_desc = y_content
        for line in desc_lines:
            c.drawString(45*mm, y_desc, line)
            y_desc -= 4*mm
        
        # Add buyer contact info at the end of column 7 (after product description)
        y_desc -= 2*mm  # Small gap after description
        
        # Mobile number
        if data.buyer.mobile:
            c.drawString(45*mm, y_desc, f"**MOBILE NUMBER : {data.buyer.mobile}")
            y_desc -= 4*mm
        
        # Tax number
        if data.buyer.tax_number:
            c.drawString(45*mm, y_desc, f"TAX NUMBER : {data.buyer.tax_number}")
            y_desc -= 4*mm
        
        # Email (if available)
        if data.buyer.email:
            c.drawString(45*mm, y_desc, f"EMAIL : {data.buyer.email}")
            y_desc -= 4*mm
        
        # Add *** at the end like in the original
        c.drawString(45*mm, y_desc, "***")
        
        # Other columns content
        y_content = y - 15*mm  # Reset for other columns
        c.drawString(125*mm, y_content, data.product.hs_code)
        
        c.setFont("Helvetica", 7)
        c.drawString(145*mm, y_content, "G.WEIGHT")
        c.drawString(145*mm, y_content - 4*mm, data.product.weight)
        
        # Invoice info
        c.drawString(170*mm, y_content, data.invoice.invoice_number)
        c.drawString(170*mm, y_content - 8*mm, data.invoice.invoice_date)
        
        # Draw table lines
        c.rect(8*mm, height - 240*mm, 194*mm, 65*mm)
        c.line(43*mm, height - 175*mm, 43*mm, height - 240*mm)  # After marks
        c.line(123*mm, height - 175*mm, 123*mm, height - 240*mm)  # After description
        c.line(143*mm, height - 175*mm, 143*mm, height - 240*mm)  # After HS code
        c.line(168*mm, height - 175*mm, 168*mm, height - 240*mm)  # After quantity
    
    def _draw_declaration_box(self, c, data: CertificateData, height):
        """Draw declaration by exporter section"""
        y = height - 245*mm
        c.setFont("Helvetica-Bold", 8)
        c.drawString(10*mm, y, "11.Declaration by the exporter")
        c.setFont("Helvetica", 7)
        
        declaration_text = """The undersigned hereby declares that the above details and statements are
correct, that all the goods were produced in China and that they comply with the
Rules of Origin of the People's Republic of China."""
        
        lines = declaration_text.split('\n')
        y_text = y - 5*mm
        for line in lines:
            c.drawString(12*mm, y_text, line.strip())
            y_text -= 3.5*mm
        
        # Place and date
        c.drawString(12*mm, y - 25*mm, f"YIWU,CHINA {data.declaration_date}")
        c.setFont("Helvetica", 6)
        c.drawString(12*mm, y - 30*mm, "Place and date,signature and stamp of authorized signatory")
        
        c.rect(8*mm, height - 285*mm, 97*mm, 45*mm)
    
    def _draw_certification_box(self, c, data: CertificateData, height):
        """Draw certification section"""
        y = height - 245*mm
        x = 107*mm
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x, y, "12.Certification")
        c.setFont("Helvetica", 7)
        c.drawString(x + 2*mm, y - 5*mm, "It is hereby certified that the declaration by the exporter is correct.")
        
        c.drawString(x + 2*mm, y - 15*mm, "ADDRESS:FIRST FLOOR,NO.288,FUTIAN ROAD,YIWU,")
        c.drawString(x + 2*mm, y - 19*mm, "ZHEJIANG")
        c.drawString(x + 2*mm, y - 23*mm, "FAX:0579-85570088 TEL:0579-85195422")
        
        c.drawString(x + 2*mm, y - 30*mm, f"YIWU,CHINA {data.declaration_date}")
        c.setFont("Helvetica", 6)
        c.drawString(x + 2*mm, y - 35*mm, "Place and date,signature and stamp of certifying authority")
        
        c.rect(105*mm, height - 285*mm, 97*mm, 45*mm)
    
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


def process_bill_of_lading(bill_pdf_path: str, api_key: str, output_path: str = None):
    """
    Main function to process a Bill of Lading and generate Certificate of Origin
    
    Args:
        bill_pdf_path: Path to the Bill of Lading PDF
        api_key: Google Gemini API key
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
    generator = CertificateGenerator()
    
    # Generate random certificate numbers
    serial_no, cert_no = generator.generate_certificate_number()
    
    # Generate declaration date (10-30 days after invoice date)
    declaration_date = generator.generate_declaration_date(invoice.invoice_date)
    
    # Create certificate data
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
    
    # Generate output path if not provided
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"certificate_of_origin_{timestamp}.pdf"
    
    # Create the certificate
    generator.create_certificate(cert_data, output_path)
    
    return output_path


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Certificate of Origin from Bill of Lading')
    parser.add_argument('bill_pdf', help='Path to Bill of Lading PDF')
    parser.add_argument('--api-key', required=True, help='Google Gemini API key')
    parser.add_argument('--output', '-o', help='Output PDF path')
    
    args = parser.parse_args()
    
    output_path = process_bill_of_lading(
        args.bill_pdf,
        args.api_key,
        args.output
    )
    
    print(f"\nCertificate generated successfully: {output_path}")


if __name__ == "__main__":
    main()
