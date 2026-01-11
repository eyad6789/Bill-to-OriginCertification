# Certificate of Origin Generator

A Python system that extracts data from Bill of Lading PDFs and generates Chinese Certificate of Origin documents using Google Gemini AI.

## Features

- **Auto Extraction**: Uses Google Gemini AI to intelligently extract data from Bill of Lading PDFs
- **Manual Entry**: Web interface for manual data input
- **PDF Generation**: Creates professional Certificate of Origin PDFs matching the official Chinese format
- **Smart Date Generation**: Automatically generates declaration dates 10-30 days after invoice date
- **Unique Certificate Numbers**: Auto-generates serial and certificate numbers

## Data Extracted/Required

| Field | Description | Example |
|-------|-------------|---------|
| Buyer Name | Company name of consignee | ASHURBANIPAL COMPANY... |
| Buyer Address | Full address | IRAQ - BAGHDAD / AL-QADISIYAH... |
| Buyer Mobile | Phone numbers | 009647901860410 |
| Buyer Tax Number | Tax ID | 902191163 |
| Seller Name | Exporter company | Yiwu Kabul Daily Necessities Factory |
| Seller Address | Exporter address | ShowRoom 602, the 6th Floor... |
| Product Description | Goods description | SIX HUNDRED FORTY (640) CTNS OF GLASS ELECTRIC KETTLE |
| HS Code | Harmonized System code | 851671.00 |
| Quantity | Number of items | 640 |
| Weight | Gross weight | 7,910 KGS G.W. |
| Port of Loading | Origin port | NINGBO CHINA |
| Port of Discharge | Destination port | UMM QASR IRAQ |
| Destination Country | Country of destination | IRAQ |
| Invoice Number | Reference number | YKDNASH7137493 |
| Invoice Date | Date of invoice | OCT.09,2025 |

## Installation

```bash
# Clone or download the project
cd certificate_origin_generator

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Option 1: Command Line

```bash
python main.py bill_of_lading.pdf --api-key YOUR_GEMINI_API_KEY --output certificate.pdf
```

### Option 2: Web Interface

```bash
python web_app.py
```

Then open http://localhost:5000 in your browser.

### Option 3: Python API

```python
from main import process_bill_of_lading

# Generate certificate from Bill of Lading
output_path = process_bill_of_lading(
    bill_pdf_path="bill_of_lading.pdf",
    api_key="YOUR_GEMINI_API_KEY",
    output_path="certificate_of_origin.pdf"
)
```

## Getting a Google Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and use it in the application

## Date Generation Logic

The declaration date is automatically calculated:
- Minimum: 10 days after invoice date
- Maximum: 30 days (1 month) after invoice date
- Random value between these bounds

Example:
- Invoice Date: OCT.09,2025
- Declaration Date: NOV.25,2025 (47 days later - within range)

## Project Structure

```
certificate_origin_generator/
├── main.py              # Core logic and CLI
├── web_app.py           # Flask web interface
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Certificate Output

The generated PDF includes:
- Header: "ORIGINAL" and "CERTIFICATE OF ORIGIN OF THE PEOPLE'S REPUBLIC OF CHINA"
- Serial and Certificate numbers
- Exporter information (Section 1)
- Consignee information (Section 2)
- Transport route (Section 3)
- Destination country (Section 4)
- Certifying authority info (Section 5)
- Goods description table (Sections 6-10)
- Declaration by exporter (Section 11)
- Certification (Section 12)

## Customization

### Modify Certificate Layout

Edit the `CertificateGenerator` class in `main.py` to adjust:
- Page dimensions
- Font sizes
- Box positions
- Text content

### Extend Data Extraction

Modify the Gemini prompt in `GeminiExtractor.extract_from_bill()` to extract additional fields.

## Error Handling

- Invalid PDF files are rejected
- Missing API key shows clear error message
- Failed extractions fall back to empty strings
- Network errors are caught and displayed

## License

This project is for educational purposes. Ensure compliance with local regulations when generating official documents.

## Support

For issues or questions, please check:
1. API key is valid and has quota
2. PDF file is readable and contains text
3. Internet connection is available for Gemini API
