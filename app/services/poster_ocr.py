"""Bounded regional OCR for illustrated scans; no inferred or corrected facts."""
import csv
import io
import shutil
import subprocess
from collections import defaultdict
import fitz


def regional_ocr(page, language):
    if not shutil.which('tesseract'):
        return None  # Use the existing PyMuPDF OCR installation instead.
    results = []
    rect = page.rect
    scale = min(2, 2400 / max(rect.width, rect.height))
    for index in range(4):
        clip = fitz.Rect(0, rect.height * index / 4, rect.width,
                         min(rect.height, rect.height * ((index + 1) / 4 + .04)))
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
        try:
            output = subprocess.run(['tesseract', 'stdin', 'stdout', '-l', language,
                                     '--psm', '6', 'tsv'], input=pix.tobytes('png'),
                                    capture_output=True, timeout=15, check=True)
        except (subprocess.SubprocessError, OSError):
            return None
        lines = defaultdict(list)
        for row in csv.DictReader(io.StringIO(output.stdout.decode('utf-8', errors='replace')), delimiter='\t'):
            text = (row.get('text') or '').strip()
            try:
                confidence = float(row['conf'])
            except (ValueError, KeyError):
                continue
            if text and confidence >= 0:
                lines[(row['block_num'], row['par_num'], row['line_num'])].append((text, confidence))
        for words in lines.values():
            meaningful = [(word, score) for word, score in words if any(c.isalnum() for c in word)]
            # Decorative fonts often score poorly even when dates/times are readable.
            # Only discard very low confidence noise; all regional OCR needs visual review.
            if not meaningful or sum(s for _, s in meaningful) / len(meaningful) < 20:
                continue
            text = ' '.join(w for w, _ in meaningful)
            if sum(c.isalnum() for c in text) >= 4:
                results.append((text, index + 1))
    return results or None
