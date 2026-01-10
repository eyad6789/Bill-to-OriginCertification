#!/usr/bin/env python3
"""
Certificate of Origin Generator - Clean Text Replacement
Uses PyMuPDF (fitz) to properly redact and replace text in PDF
This creates professional output without overlapping text
"""

import os
import json
import random
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Tuple
import re

import fitz  # PyMuPDF
import pdfplumber

# For Gemini API
try:
    from google import genai
    USE_NEW_GENAI = True
except ImportError:
    try:
        import google.generativeai as genai
        USE_NEW_GENAI = False
    except ImportError:
        USE_NEW_GENAI = None


@dataclass
class BuyerInfo:
    name: str
    address: str
    mobile: str = ""
    tax_number: str = ""
    email: str = ""


@dataclass
class SellerInfo:
    name: str
    address: str


@dataclass
class ProductInfo:
    description: str
    hs_code: str
    quantity: str
    weight: str
    marks_numbers: str = "N/M"


@dataclass
class ShippingInfo:
    port_of_loading: str
    port_of_discharge: str
    destination_country: str


@dataclass
class InvoiceInfo:
    invoice_number: str
    invoice_date: str


@dataclass
class CertificateData:
    buyer: BuyerInfo
    seller: SellerInfo
    product: ProductInfo
    shipping: ShippingInfo
    invoice: InvoiceInfo
    certificate_number: str = ""
    serial_number: str = ""
    declaration_date: str = ""


class CleanPDFGenerator:
    """
    Generate Certificate of Origin by cleanly replacing text in template PDF
    Uses redaction to remove old text, then inserts new text
    """
    
    def __init__(self, template_path: str):
        self.template_path = template_path
        
        # Define text replacement areas
        # Format: (x0, y0, x1, y1) - coordinates in PDF points from TOP-LEFT
        # These define rectangular areas where text will be redacted and replaced
        self.replacement_zones = {
            # Section 1: Exporter info
            'exporter': {
                'rect': (47, 47, 300, 75),  # Area containing exporter name and address
                'font_size': 8,
                'line_height': 8,
            },
            # Serial number 
            'serial_no': {
                'rect': (340, 38, 520, 48),
                'font_size': 8,
            },
            # Certificate number
            'cert_no': {
                'rect': (340, 51, 520, 62),
                'font_size': 8,
            },
            # Section 2: Consignee
            'consignee': {
                'rect': (47, 117, 300, 175),
                'font_size': 7,
                'line_height': 9,
            },
            # Section 3: Transport
            'transport': {
                'rect': (47, 188, 300, 198),
                'font_size': 8,
            },
            # Section 4: Destination
            'destination': {
                'rect': (47, 278, 150, 290),
                'font_size': 8,
            },
            # Section 6: Marks
            'marks': {
                'rect': (47, 338, 100, 350),
                'font_size': 8,
            },
            # Section 7: Goods description
            'goods': {
                'rect': (115, 338, 340, 395),
                'font_size': 8,
                'line_height': 10,
            },
            # Section 8: HS Code
            'hs_code': {
                'rect': (395, 338, 450, 350),
                'font_size': 8,
            },
            # Section 9: Weight
            'weight': {
                'rect': (455, 338, 500, 360),
                'font_size': 7,
                'line_height': 8,
            },
            # Section 10: Invoice number
            'invoice_no': {
                'rect': (505, 338, 565, 352),
                'font_size': 7,
            },
            # Section 10: Invoice date
            'invoice_date': {
                'rect': (495, 352, 565, 365),
                'font_size': 7,
            },
            # Declaration date (Section 11)
            'decl_date_11': {
                'rect': (47, 783, 180, 795),
                'font_size': 8,
            },
            # Declaration date (Section 12)
            'decl_date_12': {
                'rect': (330, 783, 470, 795),
                'font_size': 8,
            },
        }
    
    def generate_declaration_date(self, invoice_date_str: str) -> str:
        """Generate declaration date 10-30 days after invoice date"""
        try:
            invoice_date = datetime.strptime(invoice_date_str, "%b.%d,%Y")
        except ValueError:
            try:
                invoice_date = datetime.strptime(invoice_date_str, "%d-%b-%Y")
            except ValueError:
                try:
                    invoice_date = datetime.strptime(invoice_date_str, "%Y-%m-%d")
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
    
    def _wrap_text(self, text: str, max_width: float, font_size: float) -> List[str]:
        """Wrap text to fit within max_width"""
        # Approximate character width
        char_width = font_size * 0.5
        max_chars = int(max_width / char_width)
        
        lines = []
        for paragraph in text.split('\n'):
            words = paragraph.split()
            current_line = ""
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                if len(test_line) <= max_chars:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
        return lines
    
    def create_certificate(self, data: CertificateData, output_path: str):
        """Create certificate by redacting and replacing text"""
        
        # Open template
        doc = fitz.open(self.template_path)
        page = doc[0]
        
        # Process each zone: redact old content, add new content
        
        # 1. Exporter
        zone = self.replacement_zones['exporter']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        
        exporter_text = f"{data.seller.name}\n{data.seller.address} ***"
        self._insert_text(page, rect, exporter_text, zone['font_size'], zone.get('line_height', 10))
        
        # 2. Serial Number
        zone = self.replacement_zones['serial_no']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        self._insert_text(page, rect, data.serial_number, zone['font_size'])
        
        # 3. Certificate Number
        zone = self.replacement_zones['cert_no']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        self._insert_text(page, rect, data.certificate_number, zone['font_size'])
        
        # 4. Consignee
        zone = self.replacement_zones['consignee']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        
        consignee_text = f"{data.buyer.name}\nADDRESS : {data.buyer.address}"
        self._insert_text(page, rect, consignee_text, zone['font_size'], zone.get('line_height', 9))
        
        # 5. Transport
        zone = self.replacement_zones['transport']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        transport_text = f"FROM {data.shipping.port_of_loading} TO {data.shipping.port_of_discharge} BY SEA"
        self._insert_text(page, rect, transport_text, zone['font_size'])
        
        # 6. Destination
        zone = self.replacement_zones['destination']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        self._insert_text(page, rect, data.shipping.destination_country, zone['font_size'])
        
        # 7. Marks
        zone = self.replacement_zones['marks']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        self._insert_text(page, rect, data.product.marks_numbers, zone['font_size'])
        
        # 8. Goods description with buyer contact info
        zone = self.replacement_zones['goods']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        
        goods_text = data.product.description
        if data.buyer.mobile:
            goods_text += f"\n**MOBILE NUMBER : {data.buyer.mobile}"
        if data.buyer.tax_number:
            goods_text += f"\nTAX NUMBER : {data.buyer.tax_number}"
        if data.buyer.email:
            goods_text += f"\nEMAIL : {data.buyer.email}"
        goods_text += "\n***"
        
        self._insert_text(page, rect, goods_text, zone['font_size'], zone.get('line_height', 10))
        
        # 9. HS Code
        zone = self.replacement_zones['hs_code']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        self._insert_text(page, rect, data.product.hs_code, zone['font_size'])
        
        # 10. Weight
        zone = self.replacement_zones['weight']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        weight_text = f"G.WEIGHT\n{data.product.weight}"
        self._insert_text(page, rect, weight_text, zone['font_size'], zone.get('line_height', 10))
        
        # 11. Invoice Number
        zone = self.replacement_zones['invoice_no']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        # Split long invoice numbers
        inv_no = data.invoice.invoice_number
        if len(inv_no) > 12:
            inv_no = inv_no[:12] + "\n" + inv_no[12:]
        self._insert_text(page, rect, inv_no, zone['font_size'], 8)
        
        # 12. Invoice Date
        zone = self.replacement_zones['invoice_date']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        self._insert_text(page, rect, data.invoice.invoice_date, zone['font_size'])
        
        # 13. Declaration dates
        date_text = f"YIWU,CHINA {data.declaration_date}"
        
        zone = self.replacement_zones['decl_date_11']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        self._insert_text(page, rect, date_text, zone['font_size'])
        
        zone = self.replacement_zones['decl_date_12']
        rect = fitz.Rect(zone['rect'])
        self._redact_area(page, rect)
        self._insert_text(page, rect, date_text, zone['font_size'])
        
        # Apply all redactions
        page.apply_redactions()
        
        # Save
        doc.save(output_path)
        doc.close()
        
        print(f"Certificate generated: {output_path}")
    
    def _redact_area(self, page, rect: fitz.Rect):
        """Add a redaction annotation (white fill) to cover existing text"""
        page.add_redact_annot(rect, fill=(1, 1, 1))  # White fill
    
    def _insert_text(self, page, rect: fitz.Rect, text: str, font_size: float, line_height: float = None):
        """Insert text into the specified rectangle"""
        if line_height is None:
            line_height = font_size + 2
        
        # Calculate available width
        width = rect.width
        
        # Wrap text
        lines = self._wrap_text(text, width, font_size)
        
        # Insert each line
        y = rect.y0 + font_size  # Start position
        for line in lines:
            if y > rect.y1:  # Don't exceed rectangle
                break
            page.insert_text(
                (rect.x0, y),
                line,
                fontsize=font_size,
                fontname="helv",  # Helvetica
                color=(0, 0, 0)  # Black
            )
            y += line_height


class GeminiExtractor:
    """Extract data from Bill of Lading using Google Gemini API"""
    
    def __init__(self, api_key: str):
        if USE_NEW_GENAI is True:
            self.client = genai.Client(api_key=api_key)
            self.model_name = 'gemini-1.5-flash'
        elif USE_NEW_GENAI is False:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            raise ImportError("Google Generative AI package not installed")
        self.api_key = api_key
    
    def extract_from_bill(self, pdf_path: str) -> dict:
        text_content = self._extract_pdf_text(pdf_path)
        
        if not text_content.strip():
            print("PDF appears to be image-based, using Gemini Vision...")
            return self._extract_from_pdf_image(pdf_path)
        
        return self._extract_from_text(text_content)
    
    def _extract_from_text(self, text_content: str) -> dict:
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
            except (FileNotFoundError, subprocess.CalledProcessError):
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(pdf_path, dpi=200)
                    for i, img in enumerate(images):
                        img.save(os.path.join(tmpdir, f"page-{i+1}.png"), 'PNG')
                except ImportError:
                    return {}
            
            image_files = sorted(Path(tmpdir).glob("page*.png"))
            
            if not image_files:
                return {}
            
            import PIL.Image
            image = PIL.Image.open(str(image_files[0]))
            
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
        return f"""
You are an expert at extracting information from shipping documents (Bill of Lading).

Extract the following information and return it as a valid JSON object:

{{
    "buyer": {{
        "name": "Company name of the consignee/buyer",
        "address": "Full address of the consignee",
        "mobile": "Mobile/phone numbers if available",
        "tax_number": "Tax number if available",
        "email": "Email if available"
    }},
    "seller": {{
        "name": "Company name of the shipper/exporter",
        "address": "Full address of the shipper"
    }},
    "product": {{
        "description": "Description of goods",
        "hs_code": "HS/Harmonized Code with decimal (e.g., '851671.00')",
        "quantity": "Number of items/cartons",
        "weight": "Gross weight with unit",
        "marks_numbers": "Container number or marks, otherwise 'N/M'"
    }},
    "shipping": {{
        "port_of_loading": "Port of loading",
        "port_of_discharge": "Port of discharge",
        "destination_country": "Destination country"
    }},
    "invoice": {{
        "invoice_number": "Invoice/reference/booking number",
        "invoice_date": "Date in format MMM.DD,YYYY (e.g., 'OCT.30,2025')"
    }}
}}

Return ONLY the JSON object, no markdown, no explanation.

{context}
"""
    
    def _parse_response(self, response) -> dict:
        try:
            response_text = response.text.strip()
            if response_text.startswith("```"):
                response_text = re.sub(r'^```json?\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Error parsing response: {e}")
            return {}
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text


def process_bill_of_lading(bill_pdf_path: str, api_key: str, template_path: str, output_path: str = None):
    """Process Bill of Lading and generate Certificate of Origin"""
    
    extractor = GeminiExtractor(api_key)
    
    print(f"Extracting data from: {bill_pdf_path}")
    extracted_data = extractor.extract_from_bill(bill_pdf_path)
    
    if not extracted_data:
        raise ValueError("Failed to extract data from Bill of Lading")
    
    print("Extracted data:")
    print(json.dumps(extracted_data, indent=2))
    
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
    
    generator = CleanPDFGenerator(template_path)
    
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
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Certificate of Origin')
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
    
    print(f"\nCertificate generated: {output_path}")


if __name__ == "__main__":
    main()
