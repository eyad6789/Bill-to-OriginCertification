#!/usr/bin/env python3
"""
Demo - Clean Certificate Generator
Properly replaces text in PDF without overlapping
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clean_generator import (
    CleanPDFGenerator, CertificateData, 
    BuyerInfo, SellerInfo, ProductInfo, ShippingInfo, InvoiceInfo
)

def generate_demo(template_path: str, output_path: str):
    """Generate demo certificate with clean text replacement"""
    
    # Sample data
    buyer = BuyerInfo(
        name="ASHURBANIPAL COMPANY FOR GENERAL TRADE IN ELECTRICAL APPLIANCES AND HOME AND OFFICE FURNITURE, TRADE AND SUPPLY OF KITCHENS, FURNITURE AND DECORATION, PROCESSING AND MARKETING OF SINGLE-USE HOUSEHOLD AND FOOD SUPPLIES.",
        address="IRAQ - BAGHDAD / AL-QADISIYAH DISTRICT - MAHALLA / 606 - ALLEY / 8 - BUILDING NO. / 74 TABARAK CENTER BUILDING FLOOR NO. 5, OFFICE NO. 9",
        mobile="009647901860410 - 009647844702070",
        tax_number="902191163",
        email=""
    )
    
    seller = SellerInfo(
        name="Yiwu Kabul Daily Necessities Factory",
        address="ShowRoom 602, the 6th Floor, No.520, Dafuzhai Village, Houzhai Sub-dist, Yiwu City, Jinhua City, Zhejiang Province"
    )
    
    product = ProductInfo(
        description="SIX HUNDRED FORTY (640) CTNS OF GLASS ELECTRIC KETTLE",
        hs_code="851671.00",
        quantity="640",
        weight="7,910 KGS G.W.",
        marks_numbers="N/M"
    )
    
    shipping = ShippingInfo(
        port_of_loading="NINGBO CHINA",
        port_of_discharge="UMM QASR IRAQ",
        destination_country="IRAQ"
    )
    
    invoice = InvoiceInfo(
        invoice_number="YKDNASH7137493",
        invoice_date="OCT.09,2025"
    )
    
    # Generate
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
    
    generator.create_certificate(cert_data, output_path)
    
    print(f"\n✅ Clean certificate generated: {output_path}")
    print(f"\n📋 Details:")
    print(f"   Serial No: {serial_no}")
    print(f"   Certificate No: {cert_no}")
    print(f"   Invoice Date: {invoice.invoice_date}")
    print(f"   Declaration Date: {declaration_date}")
    
    return output_path


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template = os.path.join(script_dir, "template.pdf")
    output = sys.argv[1] if len(sys.argv) > 1 else "clean_certificate.pdf"
    
    if not os.path.exists(template):
        print(f"❌ Template not found: {template}")
        sys.exit(1)
    
    generate_demo(template, output)
