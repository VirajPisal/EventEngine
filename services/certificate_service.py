"""
Certificate Service - Generates participation certificates for online events
"""
import base64
import io
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Dict
from utils.logger import logger
import os

class CertificateService:
    """Service for generating and managing participant certificates"""

    @staticmethod
    def generate_certificate(
        participant_name: str,
        event_name: str,
        template_base64: str,
        completion_date: str = ""
    ) -> Optional[str]:
        """
        Draw participant name on the certificate template and return base64 result
        """
        try:
            # Decode template
            if 'base64,' in template_base64:
                template_base64 = template_base64.split('base64,')[1]
            
            image_data = base64.b64decode(template_base64)
            img = Image.open(io.BytesIO(image_data))
            draw = ImageDraw.Draw(img)
            
            # Width and Height
            W, H = img.size
            
            # Use a default font if custom one not available
            try:
                # Try to find a standard font on the system (Windows specific here, can be generalized)
                font_path = "C:/Windows/Fonts/arial.ttf"
                if not os.path.exists(font_path):
                    font_path = "arial.ttf"
                
                font_large = ImageFont.truetype(font_path, int(H * 0.08)) # Name font size
                font_small = ImageFont.truetype(font_path, int(H * 0.03)) # Date font size
            except:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()

            # 1. DRAW NAME (Centered)
            name_text = participant_name.upper()
            _, _, w, h = draw.textbbox((0, 0), name_text, font=font_large)
            draw.text(((W-w)/2, (H-h)/2), name_text, font=font_large, fill="black") # Assuming center for name

            # 2. DRAW EVENT NAME (Slightly below center)
            event_text = f"FOR ATTENDING: {event_name}"
            _, _, we, he = draw.textbbox((0, 0), event_text, font=font_small)
            draw.text(((W-we)/2, (H-he)/2 + h + 20), event_text, font=font_small, fill="#444444")

            # 3. DRAW DATE (Bottom right area or where appropriate)
            if completion_date:
                date_text = f"Date: {completion_date}"
                _, _, wd, hd = draw.textbbox((0, 0), date_text, font=font_small)
                draw.text((W - wd - 50, H - hd - 50), date_text, font=font_small, fill="black")

            # Save to buffer
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return img_str
            
        except Exception as e:
            logger.error(f"[CERTIFICATE] Failed to generate: {e}")
            return None
