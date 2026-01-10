#!/usr/bin/env python3
"""
Demo script - Generate Certificate of Origin without API key
Uses sample data extracted from the provided bill.pdf
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (
    CertificateGenerator, CertificateData, 
    BuyerInfo, SellerInfo, ProductInfo, ShippingInfo, InvoiceInfo
)

def generate_demo_certificate(output_path: str):
    """
    Generate a demo certificate using data from the sample bill.pdf
    """
    
    # Data extracted from bill.pdf (visible in the document images)
    buyer = BuyerInfo(
        name="ASHURBANIPAL COMPANY FOR GENERAL TRADE IN ELECTRICAL APPLIANCES AND HOME AND OFFICE FURNITURE, TRADE AND SUPPLY OF KITCHENS, FURNITURE AND DECORATION, PROCESSING AND MARKETING OF SINGLE-USE HOUSEHOLD AND FOOD SUPPLIES.",
        address="IRAQ - BAGHDAD / AL-QADISIYAH DISTRICT - MAHALLA / 606 - ALLEY / 8 - BUILDING NO. / 74 TABARAK CENTER BUILDING FLOOR NO. 5, OFFICE NO. 9",
        mobile="009647901860410 - 009647844702070",
        tax_number="902191163",
        email=""
    )
    
    seller = SellerInfo(
        name="YIWU WUJU TRADING CO.,LTD",
        address="ROOM 402, UNIT, BUILDING 21, XIAWANG SECOND DISTRICT, JIANGDONG STREET, YIWU CITY, ZHEJIANG, CHINA"
    )
    
    product = ProductInfo(
        description="SIX HUNDRED FORTY (640) CARTON(S) of GLASS ELECTRIC KETTLE",
        hs_code="851671.00",
        quantity="640",
        weight="7,910 KGS G.W.",
        marks_numbers="MSBU7137493"
    )
    
    shipping = ShippingInfo(
        port_of_loading="SHEKOU CHINA",
        port_of_discharge="UMM QASR PT, IRAQ",
        destination_country="IRAQ"
    )
    
    invoice = InvoiceInfo(
        invoice_number="181AS25S0604155X1",
        invoice_date="OCT.30,2025"
    )
    
    # Generate certificate
    generator = CertificateGenerator()
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
    print(f"\n✅ Demo certificate generated: {output_path}")
    print(f"\n📋 Certificate Details:")
    print(f"   Serial No: {serial_no}")
    print(f"   Certificate No: {cert_no}")
    print(f"   Invoice Date: {invoice.invoice_date}")
    print(f"   Declaration Date: {declaration_date}")
    
    return output_path


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "demo_certificate.pdf"
    generate_demo_certificate(output)
