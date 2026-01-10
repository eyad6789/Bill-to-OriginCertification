#!/usr/bin/env python3
"""
Demo script - Generate Certificate of Origin using original template
Uses sample data and overlays on the original certificate PDF
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from template_generator import (
    TemplateBasedGenerator, CertificateData, 
    BuyerInfo, SellerInfo, ProductInfo, ShippingInfo, InvoiceInfo
)

def generate_demo_certificate(template_path: str, output_path: str):
    """
    Generate a demo certificate using the original template
    """
    
    # Sample data (from bill.pdf)
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
    
    # Generate certificate using template
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
    
    generator.create_certificate(cert_data, output_path)
    
    print(f"\n✅ Certificate generated using template: {output_path}")
    print(f"\n📋 Certificate Details:")
    print(f"   Serial No: {serial_no}")
    print(f"   Certificate No: {cert_no}")
    print(f"   Invoice Date: {invoice.invoice_date}")
    print(f"   Declaration Date: {declaration_date}")
    print(f"\n🎨 Template used: {template_path}")
    print(f"   (Blue colors, seals, and signatures preserved!)")
    
    return output_path


if __name__ == "__main__":
    # Default paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template = os.path.join(script_dir, "template.pdf")
    output = sys.argv[1] if len(sys.argv) > 1 else "certificate_from_template.pdf"
    
    if not os.path.exists(template):
        print(f"❌ Template not found: {template}")
        print("Please provide the original certificate PDF as template.pdf")
        sys.exit(1)
    
    generate_demo_certificate(template, output)
