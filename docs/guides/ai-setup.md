# AI & Scanner Setup Guide

This guide explains how to configure the AI features in Fulcrum and use the Product Scanner efficiently.

## 1. Configuring AI (Google Gemini)

To enable AI-powered product identification (Visual Search), you need to configure an API key.

1.  **Get an API Key**:
    *   Go to [Google AI Studio](https://aistudio.google.com/).
    *   Create a new API Key.
    *   Copy the key.

2.  **Configure in Fulcrum**:
    *   Navigate to **Settings** -> **AI & Agents**.
    *   Under **Google Gemini**, paste your API Key.
    *   Click **Save Changes**.

3.  **Verification**:
    *   The status should change to "Configured".
    *   You can now use the "AI Scan" feature in the Product Scanner.

## 2. Using the Product Scanner

The scanner supports both AI Visual Search and Standard Barcode/QR Scanning.

### Modes

*   **AI Powered**:
    *   Take a photo or upload an image of a product.
    *   The system analyzes the image to identify the product (Name, Brand) and searches the database.
*   **Barcode Scanner**:
    *   Use the device camera to scan standard barcodes (UPC, EAN, Code 128) or QR Codes.
    *   **External Scanners**: You can also use a Bluetooth/USB handheld scanner. Just ensure the scanner dialog is open and scan the code.

### Product Creation

*   When adding a new product, you can:
    *   **Scan/Enter Barcode**: Input the manufacturer's barcode.
    *   **Generate Store Barcode**: Click the "Generate Store Barcode" button to create a unique internal barcode (Format: `STORE-{SKU}`).

## 3. Printed Barcodes & QR Codes

*   **Barcode**: Used for scanning at POS or Inventory checks.
*   **QR Code**: Contains a deep link (e.g., `fulcrum-product:{id}`) that can be used to quickly open the product details in the management app. Future updates will support "Double Links" for public store access.
