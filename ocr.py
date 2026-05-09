"""
OCR module using Tesseract.
"""

import logging

import cv2
import pytesseract
from pytesseract import Output

from config import Config

logger = logging.getLogger(__name__)


class Tesseract_Ocr:
    """Wrapper around pytesseract for OCR on screenshots."""

    def __init__(self) -> None:
        config = Config()
        pytesseract.pytesseract.tesseract_cmd = config.tesseract_cmd
        self._languages = config.ocr_languages

    def get_ocr_tesseract(
        self, screenshot
    ) -> tuple[dict, str]:
        """Run OCR on a BGR screenshot.

        Returns
        -------
        result : dict
            Pytesseract ``image_to_data`` output dictionary.
        str_result : str
            Full-text OCR result.
        """
        screenshot_bgr = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        str_result = pytesseract.image_to_string(screenshot_bgr, lang=self._languages)
        result = pytesseract.image_to_data(screenshot_bgr, output_type=Output.DICT)
        logger.debug("OCR detected %d tokens", len(result.get("text", [])))
        return result, str_result
