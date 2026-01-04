# Product Scanner Guide

Use the Product Scanner to quickly identify products and add them to your
inventory using AI or barcode scanning.

## Opening the Scanner

1. Go to **Products → Product Hub**
2. Click the **Scan** button (camera icon in the toolbar)

## Scanning Methods

### AI-Powered Image Scan (Camera Tab)

Take a photo of any product to identify it automatically:

1. Click **Start Camera**
2. Point at the product and click **Capture**
3. The AI analyzes the image and returns:
   - Product name and brand
   - Suggested category
   - Estimated price
   - Dimensions and weight (if found online)
4. Review the results:
   - **Product exists?** → Opens product details
   - **New product?** → Opens creation form with data pre-filled

### Barcode Scanner (Barcode Tab)

Scan standard barcodes or QR codes:

1. Click **Start Camera** or use a **Bluetooth/USB scanner**
2. Point at the barcode
3. Supported formats: UPC, EAN, Code 128, QR Code
4. If found → Opens product details
5. If not found → Opens creation form with barcode pre-filled

## Setting Up AI Features

Before using AI scanning, configure your API key:

1. Go to **Settings → AI & Agents**
2. Enable **AI Features**
3. Select **Google** as the provider
4. Enter your API key from [Google AI Studio](https://aistudio.google.com/)
5. Click **Save**

> **Tip:** Google Gemini offers a free tier that's perfect for getting started!

## Using External Barcode Scanners

Fulcrum works with any Bluetooth or USB barcode scanner:

1. Pair your scanner with your device
2. Open the Product Scanner dialog
3. Scan any barcode – it will be automatically detected
4. The result appears instantly

## Creating Products from Scans

When scanning a new product:

1. **AI Results** are pre-filled into the form:
   - Name, brand, category
   - Price estimate
   - Dimensions (if available)

2. **Barcode** is automatically saved to the product

3. Review and adjust any details, then click **Save**

## Generating Store Barcodes

For products without manufacturer barcodes:

1. Open the product creation form
2. Click **Generate Store Barcode**
3. A unique barcode is created: `STORE-{SKU}`
4. Print the barcode label for your inventory

## Tips for Best Results

- **Good lighting:** AI works better with well-lit images
- **Clear view:** Capture the full product, including logos and text
- **Multiple angles:** If one scan fails, try a different angle
- **Barcode backup:** When AI is unsure, scan the barcode for accuracy
