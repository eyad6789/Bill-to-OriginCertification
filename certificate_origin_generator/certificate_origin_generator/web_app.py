#!/usr/bin/env python3
"""
Web Interface for Certificate of Origin Generator
Flask-based web application for uploading Bill of Lading and generating certificates
"""

from flask import Flask, render_template_string, request, send_file, jsonify
import os
import tempfile
from werkzeug.utils import secure_filename
from main import process_bill_of_lading, GeminiExtractor, CertificateGenerator, CertificateData
from main import BuyerInfo, SellerInfo, ProductInfo, ShippingInfo, InvoiceInfo
import json

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Certificate of Origin Generator</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        .header p {
            opacity: 0.8;
            font-size: 14px;
        }
        .content {
            padding: 30px;
        }
        .section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .section h3 {
            color: #1a1a2e;
            margin-bottom: 15px;
            font-size: 18px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }
        .form-group input, .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .form-group textarea {
            min-height: 80px;
            resize: vertical;
        }
        .row {
            display: flex;
            gap: 15px;
        }
        .row .form-group {
            flex: 1;
        }
        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: #f8f9ff;
        }
        .upload-area:hover {
            background: #eef1ff;
            border-color: #764ba2;
        }
        .upload-area.dragover {
            background: #e3e7ff;
            border-color: #764ba2;
        }
        .upload-area input[type="file"] {
            display: none;
        }
        .upload-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .btn-secondary {
            background: #6c757d;
        }
        .btn-block {
            display: block;
            width: 100%;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            flex: 1;
            padding: 15px;
            background: #f0f0f0;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
        }
        .tab.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 30px;
        }
        .spinner {
            width: 50px;
            height: 50px;
            border: 5px solid #f3f3f3;
            border-top: 5px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .file-info {
            display: none;
            background: #e8f5e9;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }
        .file-info.show {
            display: block;
        }
        .api-key-section {
            background: #fff3cd;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #ffc107;
        }
        .api-key-section h4 {
            color: #856404;
            margin-bottom: 10px;
        }
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .checkbox-group input[type="checkbox"] {
            width: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏭 Certificate of Origin Generator</h1>
            <p>Extract data from Bill of Lading and generate Certificate of Origin (China)</p>
        </div>
        
        <div class="content">
            <div class="api-key-section">
                <h4>🔑 Google Gemini API Key</h4>
                <div class="form-group">
                    <input type="password" id="apiKey" placeholder="Enter your Gemini API key" 
                           value="{{ api_key or '' }}">
                    <small>Get your API key from <a href="https://makersuite.google.com/app/apikey" target="_blank">Google AI Studio</a></small>
                </div>
            </div>
            
            <div class="tabs">
                <button class="tab active" onclick="switchTab('auto')">📄 Auto Extract from Bill</button>
                <button class="tab" onclick="switchTab('manual')">✏️ Manual Entry</button>
            </div>
            
            <div id="alert-container"></div>
            
            <!-- Auto Extract Tab -->
            <div id="tab-auto" class="tab-content active">
                <div class="section">
                    <h3>📤 Upload Bill of Lading</h3>
                    <div class="upload-area" id="dropZone" onclick="document.getElementById('billFile').click()">
                        <div class="upload-icon">📋</div>
                        <p>Click to upload or drag and drop</p>
                        <p style="font-size: 12px; color: #666; margin-top: 10px;">PDF files only</p>
                        <input type="file" id="billFile" accept=".pdf" onchange="handleFileSelect(this)">
                    </div>
                    <div class="file-info" id="fileInfo">
                        <strong>Selected file:</strong> <span id="fileName"></span>
                    </div>
                </div>
                
                <button class="btn btn-block" id="extractBtn" onclick="extractAndGenerate()" disabled>
                    🔍 Extract Data & Generate Certificate
                </button>
            </div>
            
            <!-- Manual Entry Tab -->
            <div id="tab-manual" class="tab-content">
                <form id="manualForm">
                    <div class="section">
                        <h3>👤 Buyer/Consignee Information</h3>
                        <div class="form-group">
                            <label>Company Name *</label>
                            <input type="text" name="buyer_name" required>
                        </div>
                        <div class="form-group">
                            <label>Address *</label>
                            <textarea name="buyer_address" required></textarea>
                        </div>
                        <div class="row">
                            <div class="form-group">
                                <label>Mobile Number</label>
                                <input type="text" name="buyer_mobile">
                            </div>
                            <div class="form-group">
                                <label>Tax Number</label>
                                <input type="text" name="buyer_tax">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Email</label>
                            <input type="email" name="buyer_email">
                        </div>
                    </div>
                    
                    <div class="section">
                        <h3>🏭 Seller/Exporter Information</h3>
                        <div class="form-group">
                            <label>Company Name *</label>
                            <input type="text" name="seller_name" required>
                        </div>
                        <div class="form-group">
                            <label>Address *</label>
                            <textarea name="seller_address" required></textarea>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h3>📦 Product Information</h3>
                        <div class="form-group">
                            <label>Description of Goods *</label>
                            <textarea name="product_description" required placeholder="e.g., SIX HUNDRED FORTY (640) CTNS OF GLASS ELECTRIC KETTLE"></textarea>
                        </div>
                        <div class="row">
                            <div class="form-group">
                                <label>HS Code *</label>
                                <input type="text" name="hs_code" required placeholder="e.g., 851671.00">
                            </div>
                            <div class="form-group">
                                <label>Quantity *</label>
                                <input type="text" name="quantity" required placeholder="e.g., 640">
                            </div>
                        </div>
                        <div class="row">
                            <div class="form-group">
                                <label>Weight *</label>
                                <input type="text" name="weight" required placeholder="e.g., 7,910 KGS G.W.">
                            </div>
                            <div class="form-group">
                                <label>Marks & Numbers</label>
                                <input type="text" name="marks_numbers" value="N/M">
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h3>🚢 Shipping Information</h3>
                        <div class="row">
                            <div class="form-group">
                                <label>Port of Loading *</label>
                                <input type="text" name="port_loading" required placeholder="e.g., NINGBO CHINA">
                            </div>
                            <div class="form-group">
                                <label>Port of Discharge *</label>
                                <input type="text" name="port_discharge" required placeholder="e.g., UMM QASR IRAQ">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Destination Country *</label>
                            <input type="text" name="destination" required placeholder="e.g., IRAQ">
                        </div>
                    </div>
                    
                    <div class="section">
                        <h3>📋 Invoice Information</h3>
                        <div class="row">
                            <div class="form-group">
                                <label>Invoice Number *</label>
                                <input type="text" name="invoice_number" required>
                            </div>
                            <div class="form-group">
                                <label>Invoice Date *</label>
                                <input type="date" name="invoice_date" required>
                            </div>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-block">📄 Generate Certificate</button>
                </form>
            </div>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Processing... Please wait</p>
            </div>
        </div>
    </div>

    <script>
        // Tab switching
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
        }
        
        // File handling
        function handleFileSelect(input) {
            if (input.files.length > 0) {
                const file = input.files[0];
                document.getElementById('fileName').textContent = file.name;
                document.getElementById('fileInfo').classList.add('show');
                document.getElementById('extractBtn').disabled = false;
            }
        }
        
        // Drag and drop
        const dropZone = document.getElementById('dropZone');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
        });
        
        dropZone.addEventListener('drop', function(e) {
            const file = e.dataTransfer.files[0];
            if (file && file.type === 'application/pdf') {
                document.getElementById('billFile').files = e.dataTransfer.files;
                handleFileSelect(document.getElementById('billFile'));
            }
        });
        
        // Show alert
        function showAlert(message, type) {
            const container = document.getElementById('alert-container');
            container.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
            setTimeout(() => container.innerHTML = '', 5000);
        }
        
        // Extract and generate
        async function extractAndGenerate() {
            const apiKey = document.getElementById('apiKey').value;
            const fileInput = document.getElementById('billFile');
            
            if (!apiKey) {
                showAlert('Please enter your Gemini API key', 'error');
                return;
            }
            
            if (!fileInput.files.length) {
                showAlert('Please select a Bill of Lading PDF', 'error');
                return;
            }
            
            const formData = new FormData();
            formData.append('bill_file', fileInput.files[0]);
            formData.append('api_key', apiKey);
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('extractBtn').disabled = true;
            
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'certificate_of_origin.pdf';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    a.remove();
                    showAlert('Certificate generated successfully!', 'success');
                } else {
                    const error = await response.json();
                    showAlert(error.error || 'Failed to generate certificate', 'error');
                }
            } catch (error) {
                showAlert('Error: ' + error.message, 'error');
            } finally {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('extractBtn').disabled = false;
            }
        }
        
        // Manual form submission
        document.getElementById('manualForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const apiKey = document.getElementById('apiKey').value;
            const formData = new FormData(this);
            formData.append('api_key', apiKey);
            
            document.getElementById('loading').style.display = 'block';
            
            try {
                const response = await fetch('/generate-manual', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'certificate_of_origin.pdf';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    a.remove();
                    showAlert('Certificate generated successfully!', 'success');
                } else {
                    const error = await response.json();
                    showAlert(error.error || 'Failed to generate certificate', 'error');
                }
            } catch (error) {
                showAlert('Error: ' + error.message, 'error');
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate', methods=['POST'])
def generate_certificate():
    """Generate certificate from uploaded Bill of Lading"""
    try:
        api_key = request.form.get('api_key')
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400
        
        if 'bill_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['bill_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_input = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_input)
        
        # Generate output path
        temp_output = os.path.join(app.config['UPLOAD_FOLDER'], 'certificate_output.pdf')
        
        # Process and generate certificate
        output_path = process_bill_of_lading(temp_input, api_key, temp_output)
        
        # Clean up input file
        os.remove(temp_input)
        
        # Send the generated file
        return send_file(
            output_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='certificate_of_origin.pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate-manual', methods=['POST'])
def generate_manual():
    """Generate certificate from manual form data"""
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
        
        # Generate certificate
        generator = CertificateGenerator()
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
        temp_output = os.path.join(app.config['UPLOAD_FOLDER'], 'certificate_manual.pdf')
        generator.create_certificate(cert_data, temp_output)
        
        return send_file(
            temp_output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='certificate_of_origin.pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
