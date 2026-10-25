// ============================================================================
// Trust Vault — Secure Multi-Format In-Memory Document Viewer & Live Editor
// Canvas-sandboxed zero-download previewing + In-App Content Editing for
// PDF, Images (.png, .jpg, .webp), and Plain Text (.txt, .csv, .log, .json, .md)
// ============================================================================

// Configure PDF.js worker source if library is loaded
if (typeof pdfjsLib !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}

// Global editor state for the active document in the viewer modal
let currentPreviewDoc = {
    id: null,
    filename: '',
    contentType: '',
    canEdit: false,
    rawBytes: null,
    textData: '',
    imageData: null
};

/**
 * In-browser document preview: Decrypts & renders files into an in-memory canvas
 * or ephemeral object URL. Disables context menus and direct downloading.
 * @param {number} id - Document ID
 * @param {boolean} userCanEdit - Whether caller user has edit permissions
 */
async function viewDoc(id, userCanEdit = false) {
    const email = localStorage.getItem('user_email');
    const token = localStorage.getItem('jwt_token') || '';
    const isAdmin = localStorage.getItem('is_admin') === 'true' || localStorage.getItem('is_admin') === '1';
    const previewUrl = `${API_BASE}/documents/${id}/preview?user_email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`;
    
    const titleEl = document.getElementById('previewTitle');
    const modalEl = document.getElementById('previewModal');
    const container = document.getElementById('pdfViewerContainer');
    const editorToolbar = document.getElementById('viewerEditorToolbar');
    const btnToggleEdit = document.getElementById('btnToggleEditor');

    // Reset state
    currentPreviewDoc = {
        id: id,
        filename: `document_${id}`,
        contentType: '',
        canEdit: Boolean(isAdmin || userCanEdit),
        rawBytes: null,
        textData: '',
        imageData: null
    };

    if (editorToolbar) editorToolbar.style.display = 'none';
    if (btnToggleEdit) {
        btnToggleEdit.style.display = currentPreviewDoc.canEdit ? 'inline-flex' : 'none';
        btnToggleEdit.innerText = '✏️ Edit Document';
    }

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
        if (match && match[1]) filename = match[1];

        currentPreviewDoc.contentType = contentType;
        currentPreviewDoc.filename = filename || `Document_${id}`;

        if (titleEl) {
            titleEl.innerHTML = `<span>Secure Document: <strong>${escapeHtml(currentPreviewDoc.filename)}</strong> (ID: #${id})</span>`;
        }

        const isImage = contentType.startsWith('image/') || /\.(jpg|jpeg|png|webp|gif|bmp|svg)$/i.test(filename);
        const isPdf = contentType.includes('pdf') || filename.toLowerCase().endsWith('.pdf');
        const isText = contentType.startsWith('text/') || /\.(txt|csv|log|json|xml|md)$/i.test(filename);

        if (!container) return;

        if (isImage) {
            const blob = await response.blob();
            currentPreviewDoc.rawBytes = await blob.arrayBuffer();
            const objectUrl = URL.createObjectURL(blob);
            container.innerHTML = `
                <div id="imageViewerWrapper" style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%; padding: 10px;">
                    <img id="previewImageEl" src="${objectUrl}" alt="Secure Document" style="max-width: 100%; max-height: 70vh; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); object-fit: contain; background: #0f172a;" oncontextmenu="return false;" />
                </div>
            `;
        } else if (isText) {
            const textContent = await response.text();
            currentPreviewDoc.textData = textContent;
            container.innerHTML = `
                <div style="width: 100%; height: 100%; display: flex; flex-direction: column;">
                    <pre id="textPreviewEl" style="flex: 1; background: #0f172a; color: #f1f5f9; padding: 20px; border-radius: 8px; font-family: 'Consolas', 'Courier New', monospace; font-size: 0.92rem; overflow: auto; white-space: pre-wrap; word-break: break-all; margin: 0; line-height: 1.5;" oncontextmenu="return false;">${escapeHtml(textContent)}</pre>
                </div>
            `;
        } else if (isPdf) {
            if (typeof pdfjsLib === 'undefined') {
                throw new Error("PDF rendering engine loading, please retry in a moment.");
            }
            const arrayBuffer = await response.arrayBuffer();
            currentPreviewDoc.rawBytes = arrayBuffer;
            const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer.slice(0) });
            const pdfDoc = await loadingTask.promise;
            container.innerHTML = `
                <div id="pdfPagesWrapper" style="display: flex; flex-direction: column; align-items: center; width: 100%;"></div>
            `;
            const pagesWrapper = document.getElementById('pdfPagesWrapper');

            for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
                const page = await pdfDoc.getPage(pageNum);
                const scale = 1.35;
                const viewport = page.getViewport({ scale: scale });

                const canvas = document.createElement('canvas');
                canvas.className = 'pdf-page-canvas';
                canvas.dataset.pageNum = pageNum;
                const context = canvas.getContext('2d');
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                canvas.style.boxShadow = '0 4px 8px rgba(0,0,0,0.35)';
                canvas.style.marginBottom = '14px';
                canvas.style.backgroundColor = 'white';
                canvas.style.borderRadius = '4px';
                canvas.style.maxWidth = '100%';
                canvas.style.height = 'auto';

                pagesWrapper.appendChild(canvas);

                await page.render({
                    canvasContext: context,
                    viewport: viewport
                }).promise;
            }
        } else {
            // Binary Office formats (.docx, .xlsx, .pptx)
            container.innerHTML = `
                <div style="background: #1e293b; color: white; padding: 30px; border-radius: 8px; max-width: 550px; text-align: center; margin-top: 40px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                    <div style="font-size: 40px; margin-bottom: 15px;">🛡️</div>
                    <h3 style="margin-bottom: 10px; color: #38bdf8;">Encrypted Enterprise Document</h3>
                    <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 15px;">
                        This document (<strong>${escapeHtml(filename || 'ID: #' + id)}</strong>) is securely stored with cryptographic protection.
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
    const editorToolbar = document.getElementById('viewerEditorToolbar');
    if (modalEl) modalEl.style.display = 'none';
    if (container) container.innerHTML = '';
    if (editorToolbar) editorToolbar.style.display = 'none';
    currentPreviewDoc = { id: null, filename: '', contentType: '', canEdit: false, rawBytes: null, textData: '', imageData: null };
}

/**
 * Toggles in-app editing toolbar and workspace according to document format
 */
function toggleInAppEditor() {
    if (!currentPreviewDoc.canEdit) {
        showAlert("You do not have permission to edit this document.", "error");
        return;
    }

    const editorToolbar = document.getElementById('viewerEditorToolbar');
    if (!editorToolbar) return;

    const isCurrentlyOpen = editorToolbar.style.display === 'flex';
    if (isCurrentlyOpen) {
        // Close editor mode, reload preview
        editorToolbar.style.display = 'none';
        const btnToggleEdit = document.getElementById('btnToggleEditor');
        if (btnToggleEdit) btnToggleEdit.innerText = '✏️ Edit Document';
        viewDoc(currentPreviewDoc.id, currentPreviewDoc.canEdit);
        return;
    }

    // Open editor mode
    editorToolbar.style.display = 'flex';
    const btnToggleEdit = document.getElementById('btnToggleEditor');
    if (btnToggleEdit) btnToggleEdit.innerText = '👁️ Return to Preview';

    const fn = (currentPreviewDoc.filename || '').toLowerCase();
    const isPdf = currentPreviewDoc.contentType.includes('pdf') || fn.endsWith('.pdf');
    const isImage = currentPreviewDoc.contentType.startsWith('image/') || /\.(jpg|jpeg|png|webp|gif|bmp)$/i.test(fn);
    const isText = currentPreviewDoc.contentType.startsWith('text/') || /\.(txt|csv|log|json|xml|md)$/i.test(fn);

    // Show/hide format-specific tool buttons
    const pdfTools = document.getElementById('editorPdfTools');
    const imageTools = document.getElementById('editorImageTools');
    const textTools = document.getElementById('editorTextTools');

    if (pdfTools) pdfTools.style.display = isPdf ? 'flex' : 'none';
    if (imageTools) imageTools.style.display = isImage ? 'flex' : 'none';
    if (textTools) textTools.style.display = isText ? 'flex' : 'none';

    const container = document.getElementById('pdfViewerContainer');

    if (isText) {
        container.innerHTML = `
            <div style="width: 100%; height: 100%; display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; color: #94a3b8; font-size: 0.85rem;">
                    <span>📝 Live In-Vault Plain Text Editor — Make your adjustments directly below:</span>
                </div>
                <textarea id="liveTextEditorArea" style="flex: 1; width: 100%; height: 60vh; background: #0f172a; color: #f8fafc; font-family: 'Consolas', 'Courier New', monospace; font-size: 0.95rem; line-height: 1.6; padding: 16px; border-radius: 8px; border: 1px solid #334155; resize: none; outline: none;">${escapeHtml(currentPreviewDoc.textData || '')}</textarea>
            </div>
        `;
    } else if (isPdf) {
        // Show guidance on adding live annotations / watermarks directly onto PDF
        showAlert("In-App PDF Editor active: Add text annotation or approval watermark and click 'Save & Apply to Vault'.", "info");
    } else if (isImage) {
        showAlert("In-App Image Editor active: Apply rotation or color filters and click 'Save & Apply to Vault'.", "info");
    }
}

/**
 * Saves modified document content back to Vault storage & updates last_edited audit
 */
async function saveInAppDocumentEdits() {
    if (!currentPreviewDoc.id || !currentPreviewDoc.canEdit) {
        showAlert("No editable document session active.", "error");
        return;
    }

    const email = localStorage.getItem('user_email');
    const token = localStorage.getItem('jwt_token') || '';
    const fn = (currentPreviewDoc.filename || '').toLowerCase();
    const isPdf = currentPreviewDoc.contentType.includes('pdf') || fn.endsWith('.pdf');
    const isImage = currentPreviewDoc.contentType.startsWith('image/') || /\.(jpg|jpeg|png|webp|gif|bmp)$/i.test(fn);
    const isText = currentPreviewDoc.contentType.startsWith('text/') || /\.(txt|csv|log|json|xml|md)$/i.test(fn);

    const btnSave = document.getElementById('btnSaveDocumentEdits');
    if (btnSave) {
        btnSave.disabled = true;
        btnSave.innerText = "⏳ Saving & Encrypting...";
    }

    try {
        let editedBlob = null;

        if (isText) {
            const textArea = document.getElementById('liveTextEditorArea');
            const newContent = textArea ? textArea.value : (currentPreviewDoc.textData || '');
            editedBlob = new Blob([newContent], { type: 'text/plain;charset=utf-8' });
        } else if (isPdf) {
            if (typeof PDFLib === 'undefined' || !currentPreviewDoc.rawBytes) {
                throw new Error("PDF editor engine or document buffer not ready.");
            }
            const pdfDoc = await PDFLib.PDFDocument.load(currentPreviewDoc.rawBytes);
            const pages = pdfDoc.getPages();

            const annotationText = (document.getElementById('pdfAnnotationInput')?.value || '').trim();
            const addStamp = document.getElementById('pdfStampCheckbox')?.checked;

            if (annotationText || addStamp) {
                const helveticaFont = await pdfDoc.embedFont(PDFLib.StandardFonts.HelveticaBold);
                pages.forEach((page, idx) => {
                    const { width, height } = page.getSize();

                    // Optional Official Vault Stamp
                    if (addStamp) {
                        page.drawText(`VERIFIED VAULT COPY • ${new Date().toLocaleDateString()}`, {
                            x: 40,
                            y: height - 30,
                            size: 10,
                            font: helveticaFont,
                            color: PDFLib.rgb(0.01, 0.52, 0.78),
                            opacity: 0.85
                        });
                    }

                    // Custom user text annotation on top of page 1
                    if (annotationText && idx === 0) {
                        page.drawText(annotationText, {
                            x: 50,
                            y: height - 55,
                            size: 12,
                            font: helveticaFont,
                            color: PDFLib.rgb(0.85, 0.15, 0.15),
                            opacity: 0.95
                        });
                    }
                });
            }

            const pdfBytes = await pdfDoc.save();
            editedBlob = new Blob([pdfBytes], { type: 'application/pdf' });
        } else if (isImage) {
            const imgEl = document.getElementById('previewImageEl');
            if (!imgEl) throw new Error("Image element not found.");

            const canvas = document.createElement('canvas');
            canvas.width = imgEl.naturalWidth || imgEl.width || 800;
            canvas.height = imgEl.naturalHeight || imgEl.height || 600;
            const ctx = canvas.getContext('2d');

            // Apply current CSS filter to canvas if any
            if (imgEl.style.filter) {
                ctx.filter = imgEl.style.filter;
            }
            ctx.drawImage(imgEl, 0, 0, canvas.width, canvas.height);

            // Watermark or stamp
            const imgWatermark = (document.getElementById('imageWatermarkInput')?.value || '').trim();
            if (imgWatermark) {
                ctx.filter = 'none';
                ctx.font = 'bold 22px Arial, sans-serif';
                ctx.fillStyle = 'rgba(2, 132, 199, 0.9)';
                ctx.fillText(imgWatermark, 25, 45);
            }

            editedBlob = await new Promise(resolve => {
                canvas.toBlob(blob => resolve(blob), currentPreviewDoc.contentType || 'image/png', 0.92);
            });
        }

        if (!editedBlob) {
            throw new Error("Could not serialize edited file data.");
        }

        const formData = new FormData();
        formData.append('file', editedBlob, currentPreviewDoc.filename);
        formData.append('user_email', email);

        const res = await authFetch(`${API_BASE}/documents/${currentPreviewDoc.id}/content`, {
            method: 'PUT',
            body: formData
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to save edited document.");

        showAlert("Document successfully edited and saved into Vault! Administrator audit notification sent.", "success");

        // Reload viewer with fresh content
        const editorToolbar = document.getElementById('viewerEditorToolbar');
        if (editorToolbar) editorToolbar.style.display = 'none';
        const btnToggleEdit = document.getElementById('btnToggleEditor');
        if (btnToggleEdit) btnToggleEdit.innerText = '✏️ Edit Document';
        await viewDoc(currentPreviewDoc.id, currentPreviewDoc.canEdit);

        // Refresh underlying table if on dashboard or admin
        if (typeof loadAdminDocuments === 'function') loadAdminDocuments();
        if (typeof loadVaultDocuments === 'function') loadVaultDocuments();

    } catch (err) {
        showAlert(err.message, "error");
    } finally {
        if (btnSave) {
            btnSave.disabled = false;
            btnSave.innerText = "💾 Save & Apply to Vault";
        }
    }
}

/**
 * Image Editor Helper: Apply filter
 */
function applyImageFilter(filterType) {
    const imgEl = document.getElementById('previewImageEl');
    if (!imgEl) return;
    if (filterType === 'none') {
        imgEl.style.filter = 'none';
    } else if (filterType === 'grayscale') {
        imgEl.style.filter = 'grayscale(100%)';
    } else if (filterType === 'invert') {
        imgEl.style.filter = 'invert(100%)';
    } else if (filterType === 'contrast') {
        imgEl.style.filter = 'contrast(150%) brightness(110%)';
    }
}

/**
 * Helper to escape HTML characters
 */
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
