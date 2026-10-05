"""PDF exporter for EGOFET Memory Dashboard.

Exports a memory to PDF using weasyprint to convert HTML.
"""

from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .html import export_memory_html, PROJECT_ROOT


def export_memory_pdf(
    memory_id: int,
    output_dir: Optional[Path] = None,
    include_figures: bool = True,
    include_photos: bool = True,
) -> Optional[Path]:
    """Export a memory to PDF file.
    
    Args:
        memory_id: ID of the memory to export
        output_dir: Directory to save the PDF file (default: output/exports/)
        include_figures: Whether to include figure images
        include_photos: Whether to include photo images
    
    Returns:
        Path to the generated PDF file, or None if export failed
    """
    try:
        from weasyprint import HTML
    except ImportError:
        print("Error: weasyprint is not installed. Install with: pip install weasyprint")
        return None
    
    if output_dir is None:
        output_dir = PROJECT_ROOT / "output" / "exports"
    
    # First, generate the HTML
    html_path = export_memory_html(
        memory_id=memory_id,
        output_dir=output_dir,
        include_figures=include_figures,
        include_photos=include_photos,
    )
    
    if not html_path:
        return None
    
    try:
        # Convert HTML to PDF
        pdf_path = html_path.with_suffix('.pdf')
        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        
        # Remove the intermediate HTML file
        html_path.unlink()
        
        return pdf_path
    except Exception as e:
        print(f"Error converting to PDF: {e}")
        # Clean up HTML if conversion failed
        if html_path.exists():
            html_path.unlink()
        return None
