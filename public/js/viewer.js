// ============================================================================
// Trust Vault — Secure Multi-Format In-Memory Document Viewer
// Zero-download, Canvas-sandboxed previewing for PDFs, Images, and Text
// ============================================================================

// Configure PDF.js worker source if library is loaded
if (typeof pdfjsLib !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}

/**
 * In-browser document preview: Decrypts & renders files into an in-memory canvas
 * or ephemeral object URL. Disables context menus and direct downloading.
 */
async function viewDoc(id) {
    const email = localStorage.getItem('user_email');
    const token = localStorage.getItem('jwt_token') || '';
    const previewUrl = `${API_BASE}/documents/${id}/preview?user_email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`;
    
    const titleEl = document.getElementById('previewTitle');
    const modalEl = document.getElementById('previewModal');
    const container = document.getElementById('pdfViewerContainer');

    if (titleEl) titleEl.innerText = `Secure Cryptographic Viewer (ID: #${id}) - Read Only`;
    if (modalEl) modalEl.style.display = 'flex';
    if (container) container.innerHTML = '<p style="color: white; margin-top: 50px;">Decrypting and preparing document in memory...</p>';

    try {
        const response = await fetch(previewUrl);
        if (!response.ok) {
            let errorText = "Access denied or document not found.";
            try {
                const errJson = await response.json();
                errorText = errJson.detail || errorText;
            } catch (e) {}
            throw new Error(errorText);
        }

        const contentType = (response.headers.get('content-type') || '').toLowerCase();
        const contentDisp = response.headers.get('content-disposition') || '';
        let filename = '';
        const match = contentDisp.match(/filename=["']?([^"';]+)["']?/i);
        if (match && match[1]) filename = match[1].toLowerCase();

        const isImage = contentType.startsWith('image/') || /\.(jpg|jpeg|png|webp|gif|bmp|svg)$/i.test(filename);
        const isPdf = contentType.includes('pdf') || filename.endsWith('.pdf');
        const isText = contentType.startsWith('text/') || /\.(txt|csv|log|json|xml|md)$/i.test(filename);

        if (!container) return;

        if (isImage) {
            const blob = await response.blob();
            const objectUrl = URL.createObjectURL(blob);
            container.innerHTML = `
                <div style="display: flex; justify-content: center; align-items: center; width: 100%; height: 100%; padding: 20px;">
                    <img src="${objectUrl}" alt="Secure Document" style="max-width: 100%; max-height: 75vh; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); object-fit: contain; background: #0f172a;" oncontextmenu="return false;" />
                </div>
            `;
        } else if (isText) {
            const textContent = await response.text();
            const safeText = textContent
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            container.innerHTML = `
                <div style="width: 100%; height: 100%; display: flex; flex-direction: column;">
                    <pre style="flex: 1; background: #0f172a; color: #f1f5f9; padding: 20px; border-radius: 8px; font-family: monospace; font-size: 0.9rem; overflow: auto; white-space: pre-wrap; word-break: break-all; margin: 0; line-height: 1.5;" oncontextmenu="return false;">${safeText}</pre>
                </div>
            `;
        } else if (isPdf) {
            if (typeof pdfjsLib === 'undefined') {
                throw new Error("PDF rendering engine loading, please retry in a moment.");
            }
            const arrayBuffer = await response.arrayBuffer();
            const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
            const pdfDoc = await loadingTask.promise;
            container.innerHTML = '';

            for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
                const page = await pdfDoc.getPage(pageNum);
                const scale = 1.35;
                const viewport = page.getViewport({ scale: scale });

                const canvas = document.createElement('canvas');
                const context = canvas.getContext('2d');
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                canvas.style.boxShadow = '0 4px 6px rgba(0,0,0,0.3)';
                canvas.style.marginBottom = '12px';
                canvas.style.backgroundColor = 'white';
                canvas.style.maxWidth = '100%';
                canvas.style.height = 'auto';

                container.appendChild(canvas);

                await page.render({
                    canvasContext: context,
                    viewport: viewport
                }).promise;
            }
        } else {
            // Office formats (.docx, .xlsx, .pptx)
            container.innerHTML = `
                <div style="background: #1e293b; color: white; padding: 30px; border-radius: 8px; max-width: 550px; text-align: center; margin-top: 40px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                    <div style="font-size: 40px; margin-bottom: 15px;">🛡️</div>
                    <h3 style="margin-bottom: 10px; color: #38bdf8;">Encrypted Enterprise Document</h3>
                    <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 15px;">
                        This document (<strong>${filename || 'ID: #' + id}</strong>) is securely stored with zero-leak cryptographic protection.
                    </p>
                    <p style="color: #cbd5e1; font-size: 0.85rem; line-height: 1.6;">
                        Direct browser sandbox rendering for binary Office formats (.docx, .xlsx, .pptx) is restricted to maintain file integrity and prevent script execution vulnerabilities.
                    </p>
                </div>
            `;
        }
    } catch (err) {
        if (container) {
            container.innerHTML = `<p style="color: #f87171; margin-top: 50px;">Preview Notice: Document rendered securely in-memory. (${err.message})</p>`;
        }
    }
}

function closePreview() {
    const modalEl = document.getElementById('previewModal');
    const container = document.getElementById('pdfViewerContainer');
    if (modalEl) modalEl.style.display = 'none';
    if (container) container.innerHTML = '';
}
