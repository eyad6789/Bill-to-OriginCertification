#!/usr/bin/env python3
"""
Demo - Word-based Certificate Generator
Clean text replacement in Word document
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from word_generator import (
    WordCertificateGenerator, CertificateData,
    BuyerInfo, SellerInfo, ProductInfo, ShippingInfo, InvoiceInfo
)

def generate_demo(template_path: str, output_path: str):
    """Generate demo certificate using Word template"""
    
    # Sample data - different from template to show replacement works
    buyer = BuyerInfo(
        name="NEW COMPANY FOR IMPORT AND EXPORT TRADING GENERAL SUPPLIES AND EQUIPMENT",
        address="IRAQ - BASRA / AL-ZUBAIR DISTRICT - STREET 15 - BUILDING NO. 42",
        mobile="009647712345678 - 009647798765432",
        tax_number="123456789",
        email="contact@newcompany.com"
    )
    
    seller = SellerInfo(
        name="Shanghai Export Trading Co., Ltd",
        address="Room 1502, Tower A, No.100 Pudong Avenue, Shanghai, China"
    )
    
    product = ProductInfo(
        description="EIGHT HUNDRED (800) CTNS OF STAINLESS STEEL COOKWARE SET",
        hs_code="732393.00",
        quantity="800",
        weight="12,500 KGS G.W.",
        marks_numbers="N/M"
    )
    
    shipping = ShippingInfo(
        port_of_loading="SHANGHAI CHINA",
        port_of_discharge="UMM QASR IRAQ",
        destination_country="IRAQ"
    )
    
    invoice = InvoiceInfo(
        invoice_number="INV2025001234",
        invoice_date="NOV.15,2025"
    )
    
    # Generate
    generator = WordCertificateGenerator(template_path)
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
    
    docx_path, pdf_path = generator.create_certificate(cert_data, output_path)
    
    print(f"\n✅ Certificate generated!")
    print(f"\n📄 Word file: {docx_path}")
    if pdf_path:
        print(f"📄 PDF file: {pdf_path}")
    print(f"\n📋 Details:")
    print(f"   Serial No: {serial_no}")
    print(f"   Certificate No: {cert_no}")
    print(f"   Invoice Date: {invoice.invoice_date}")
    print(f"   Declaration Date: {declaration_date}")
    print(f"\n🏢 New Seller: {seller.name}")
    print(f"🏪 New Buyer: {buyer.name[:50]}...")
    
    return docx_path, pdf_path


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template = os.path.join(script_dir, "template.docx")
    output = sys.argv[1] if len(sys.argv) > 1 else "word_certificate.docx"
    
    if not os.path.exists(template):
        print(f"❌ Template not found: {template}")
        print("Please provide the Word template as template.docx")
        sys.exit(1)
    
    generate_demo(template, output)
