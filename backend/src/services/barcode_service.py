"""
Barcode and QR Code Generator Service.

The `python-barcode` and `qrcode` packages are optional — when the
backend image hasn't been rebuilt after they were added to
`requirements.txt`, every call here used to raise an `ImportError`
at module-import time and the surrounding code logged a noisy
"Error generating barcodes" line on every product create. We now
defer the imports + skip silently when the modules are missing so
the rest of the workspace stays usable on a stale image.
"""
import io
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class BarcodeService:
    """
    Generates Barcode and QR Code images.
    Returns them as base64 strings or bytes for storage.
    """

    @staticmethod
    def generate_barcode(data: str, code_type: str = 'code128') -> Optional[bytes]:
        """
        Generate a linear barcode (CODE128, EAN13). Returns None when
        the optional `python-barcode` package isn't installed.
        """
        try:
            import barcode
            from barcode.writer import ImageWriter
        except ImportError:
            logger.debug("python-barcode not installed; skipping barcode generation")
            return None
        try:
            # Code128 is robust for alphanumeric
            barcode_class = barcode.get_barcode_class(code_type)
            # writer=ImageWriter() requires pillow
            my_barcode = barcode_class(data, writer=ImageWriter())

            buffer = io.BytesIO()
            my_barcode.write(buffer)
            return buffer.getvalue()
        except Exception as e:
            logger.warning("Error generating barcode: %s", e)
            return None

    @staticmethod
    def generate_qrcode(data: str) -> Optional[bytes]:
        """
        Generate a QR code. Returns None when `qrcode` isn't installed.
        """
        try:
            import qrcode
        except ImportError:
            logger.debug("qrcode not installed; skipping QR generation")
            return None
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception as e:
            logger.warning("Error generating QR code: %s", e)
            return None

    @staticmethod
    def generate_codes_for_product(product_id: int, sku: str) -> Tuple[Optional[bytes], Optional[bytes]]:
        """
        Helper to generate both codes for a product.
        QR Code links to: https://fulcrum.app/p/{product_id} (example)
        """
        barcode_bytes = BarcodeService.generate_barcode(sku) if sku else None
        qr_data = f"https://fulcrum.app/p/{product_id}"
        qr_bytes = BarcodeService.generate_qrcode(qr_data)
        
        return barcode_bytes, qr_bytes
