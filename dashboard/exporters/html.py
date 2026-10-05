"""HTML exporter for EGOFET Memory Dashboard.

Exports a memory to a self-contained HTML file with embedded images.
"""

import base64
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src import db


PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _image_to_base64(image_path: Path) -> Optional[str]:
    """Convert an image file to base64 data URI."""
    try:
        if not image_path.exists():
            return None
        
        # Determine format from extension
        ext = image_path.suffix.lower()
        if ext in ['.jpg', '.jpeg']:
            fmt = 'JPEG'
        elif ext == '.png':
            fmt = 'PNG'
        else:
            return None
        
        img = Image.open(image_path)
        buffer = io.BytesIO()
        img.save(buffer, format=fmt)
        img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        mime_type = f'image/{fmt.lower()}'
        return f'data:{mime_type};base64,{img_data}'
    except Exception as e:
        print(f"Warning: Could not load image {image_path}: {e}")
        return None


def _csv_to_figure_base64(csv_path: Path) -> Optional[str]:
    """Convert a CSV file to a matplotlib figure and return as base64."""
    try:
        if not csv_path.exists():
            return None
        
        import matplotlib.pyplot as plt
        
        df = pd.read_csv(csv_path)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if 'V_th (V)' in df.columns and 'measurement' in df.columns:
            # Vth extraction results
            ax.bar(range(len(df)), df['V_th (V)'], color='steelblue')
            ax.set_xlabel('Measurement Index')
            ax.set_ylabel('V_th (V)')
            ax.set_title(f'V_th Extraction - {csv_path.stem}')
            ax.set_xticks(range(len(df)))
            ax.set_xticklabels(df['measurement'], rotation=45, ha='right')
        else:
            # Generic data
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if len(numeric_cols) >= 2:
                ax.plot(df[numeric_cols[0]], df[numeric_cols[1]], 'o-')
                ax.set_xlabel(numeric_cols[0])
                ax.set_ylabel(numeric_cols[1])
                ax.set_title(csv_path.stem)
            else:
                plt.close(fig)
                return None
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        plt.close(fig)
        buffer.seek(0)
        
        img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{img_data}'
    except Exception as e:
        print(f"Warning: Could not generate figure from {csv_path}: {e}")
        return None


def export_memory_html(
    memory_id: int,
    output_dir: Optional[Path] = None,
    include_figures: bool = True,
    include_photos: bool = True,
) -> Optional[Path]:
    """Export a memory to HTML file.
    
    Args:
        memory_id: ID of the memory to export
        output_dir: Directory to save the HTML file (default: output/exports/)
        include_figures: Whether to include figure images
        include_photos: Whether to include photo images
    
    Returns:
        Path to the generated HTML file, or None if export failed
    """
    if output_dir is None:
        output_dir = PROJECT_ROOT / "output" / "exports"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load memory from database
    memory = db.get_memory(memory_id)
    if not memory:
        print(f"Error: Memory {memory_id} not found")
        return None
    
    # Separate fields
    base_fields = [f for f in memory['fields'] if f['field_type'] == 'base']
    custom_fields = [f for f in memory['fields'] if f['field_type'] == 'custom']
    
    # Process references
    figures = []
    photos = []
    
    for ref in memory['references']:
        ref_path = PROJECT_ROOT / ref['ref_path']
        
        if ref['ref_type'] == 'csv' and include_figures:
            # Convert CSV to figure
            img_data = _csv_to_figure_base64(ref_path)
            if img_data:
                figures.append({'data': img_data, 'path': ref['ref_path']})
        
        elif ref['ref_type'] == 'figure' and include_figures:
            # Load figure image
            img_data = _image_to_base64(ref_path)
            if img_data:
                figures.append({'data': img_data, 'path': ref['ref_path']})
        
        elif ref['ref_type'] == 'photo' and include_photos:
            # Load photo
            img_data = _image_to_base64(ref_path)
            if img_data:
                photos.append({'data': img_data, 'path': ref['ref_path']})
    
    # Render template
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template('memory.html')
    
    html_content = template.render(
        memory=memory,
        base_fields=base_fields,
        custom_fields=custom_fields,
        references=memory['references'],
        analysis_results=memory['analysis_results'],
        figures=figures,
        photos=photos,
        export_date=datetime.now().strftime('%Y-%m-%d %H:%M'),
    )
    
    # Save HTML file
    output_filename = f"{memory['title'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    output_path = output_dir / output_filename
    output_path.write_text(html_content, encoding='utf-8')
    
    return output_path
