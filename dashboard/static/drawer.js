// Drawer resize functionality
(function() {
    const drawers = document.querySelectorAll('.nicegui-drawer');
    
    drawers.forEach(drawer => {
        const resizer = document.createElement('div');
        resizer.className = 'drawer-resizer';
        drawer.appendChild(resizer);
        
        let isResizing = false;
        let startX, startWidth;
        
        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = drawer.offsetWidth;
            document.body.style.cursor = 'col-resize';
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            
            const width = startWidth + (e.clientX - startX);
            if (width >= 200 && width <= 800) {
                drawer.style.width = width + 'px';
            }
        });
        
        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
            }
        });
    });
})();
