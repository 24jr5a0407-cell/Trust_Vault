import os
import re
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from config import MAX_UPLOAD_SIZE_BYTES, MAX_UPLOAD_SIZE_MB
from logger import logger

# Enterprise Whitelist of Permitted Document & Media Formats
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".txt",
    ".csv",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}

# Explicitly Blocked High-Risk Executable and Script Extensions
BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".bash", ".php", ".py", ".pl", ".cgi",
    ".js", ".jsp", ".asp", ".aspx", ".vbs", ".msi", ".dll", ".com", ".scr",
    ".pif", ".jar", ".apk", ".iso", ".bin", ".elf", ".ps1", ".app", ".dmg",
    ".reg", ".wsf", ".hta", ".cpl", ".inf"
}

# Malicious script patterns and webshell injection signatures
DANGEROUS_SIGNATURES = [
    (b"<?php", "Embedded PHP script"),
    (b"<?=", "Embedded PHP short tag"),
    (b"<script", "Embedded HTML/JavaScript payload"),
    (b"powershell -", "PowerShell invocation script"),
    (b"eval(", "Dynamic code execution statement"),
    (b"base64_decode(", "Obfuscated payload decoding function"),
    (b"system(", "System command execution function")
]


def sanitize_filename(filename: str) -> str:
    """Sanitizes filename, preventing directory traversal and null byte injection."""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    # Check for null byte injection
    if "\x00" in filename:
        logger.warning(f"Security Alert: Null byte injection attempt detected in filename: {repr(filename)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malicious filename characters detected."
        )

    # Prevent path traversal
    clean_name = os.path.basename(filename).strip()
    if not clean_name or clean_name in (".", ".."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename specified."
        )

    # Prevent hidden files
    if clean_name.startswith("."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hidden files cannot be uploaded."
        )

    # Check for dangerous double extensions (e.g. invoice.pdf.exe)
    parts = clean_name.lower().split(".")
    if len(parts) > 2:
        for p in parts[1:-1]:
            ext_check = f".{p}"
            if ext_check in BLOCKED_EXTENSIONS:
                logger.warning(f"Security Alert: Dangerous double-extension detected: {clean_name}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dangerous double extension detected: '{ext_check}'."
                )

    return clean_name


def verify_magic_bytes(ext: str, content: bytes, filename: str) -> None:
    """Validates the file's binary magic byte signature against its claimed extension."""
    if ext == ".pdf":
        if not content.startswith(b"%PDF-"):
            logger.warning(f"Security Alert: Spoofed PDF detected for {filename}. Missing %PDF- header.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match a valid PDF document (spoofed extension detected)."
            )

    elif ext == ".png":
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            logger.warning(f"Security Alert: Spoofed PNG detected for {filename}.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match a valid PNG image."
            )

    elif ext in (".jpg", ".jpeg"):
        if not content.startswith(b"\xff\xd8\xff"):
            logger.warning(f"Security Alert: Spoofed JPEG detected for {filename}.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match a valid JPEG image."
            )

    elif ext == ".webp":
        if not (content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP"):
            logger.warning(f"Security Alert: Spoofed WebP detected for {filename}.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match a valid WebP image."
            )

    elif ext in (".docx", ".xlsx", ".pptx"):
        # Microsoft Office OpenXML documents are ZIP archives starting with PK\x03\x04
        if not content.startswith(b"PK\x03\x04"):
            logger.warning(f"Security Alert: Spoofed Office OpenXML document detected for {filename}.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File content does not match a valid Office document ({ext})."
            )

    elif ext in (".txt", ".csv"):
        # Plain text must be readable and free of binary null bytes
        if b"\x00" in content[:4096]:
            logger.warning(f"Security Alert: Binary content detected in text document {filename}.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Binary characters are not permitted in plain text or CSV files."
            )


def scan_for_malicious_payloads(content: bytes, filename: str) -> None:
    """Scans binary content for executable headers and dangerous code snippets."""
    sample = content[:16384].lower()

    # Check for executable and script headers strictly at byte offset 0
    if content.startswith(b"MZ"):
        logger.warning(f"Security Alert: Blocked executable binary (MZ) disguised as {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security scan rejected file: Potentially harmful content detected (Windows PE executable binary (MZ header))."
        )

    if content.startswith(b"\x7fELF"):
        logger.warning(f"Security Alert: Blocked ELF executable disguised as {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security scan rejected file: Potentially harmful content detected (Linux/UNIX ELF executable binary)."
        )

    if content.startswith(b"\xca\xfe\xba\xbe"):
        logger.warning(f"Security Alert: Blocked Java class file disguised as {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security scan rejected file: Potentially harmful content detected (Compiled Java class file)."
        )

    if content.startswith(b"#!/bin/sh") or content.startswith(b"#!/bin/bash"):
        logger.warning(f"Security Alert: Blocked shell script disguised as {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security scan rejected file: Potentially harmful content detected (Shell script execution header)."
        )

    # Scan for malicious webshell and script injection payloads
    for sig, desc in DANGEROUS_SIGNATURES:
        if sig.lower() in sample:
            logger.warning(f"Security Alert: Malicious payload detected in {filename}: {desc}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security scan rejected file: Potentially harmful content detected ({desc})."
            )


def validate_file_upload(file: UploadFile) -> tuple[str, bytes]:
    """
    Complete production validation pipeline:
    1. Filename sanitization and path traversal prevention
    2. Extension whitelisting and blocklisting
    3. File size constraints enforcement
    4. Magic byte signature verification
    5. Malicious executable / script payload scanning
    Returns: (clean_filename, file_bytes)
    """
    raw_name = file.filename or ""
    clean_name = sanitize_filename(raw_name)
    ext = Path(clean_name).suffix.lower()

    if not ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Files without an extension cannot be uploaded."
        )

    if ext in BLOCKED_EXTENSIONS:
        logger.warning(f"Security Alert: Blocked extension upload attempt: '{clean_name}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File format '{ext}' is considered harmful and is strictly blocked."
        )

    if ext not in ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
        logger.warning(f"Rejected unsupported file extension: '{clean_name}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {allowed_list}"
        )

    # Read and inspect content size
    file_bytes = file.file.read()
    file_size = len(file_bytes)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty files (0 bytes) cannot be uploaded."
        )

    if file_size > MAX_UPLOAD_SIZE_BYTES:
        logger.warning(f"Upload rejected: {clean_name} ({file_size} bytes) exceeds {MAX_UPLOAD_SIZE_MB}MB limit.")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowable size of {MAX_UPLOAD_SIZE_MB}MB."
        )

    # Verify Magic Bytes & Scan for Malicious Signatures
    verify_magic_bytes(ext, file_bytes, clean_name)
    scan_for_malicious_payloads(file_bytes, clean_name)

    logger.info(f"File validation passed: '{clean_name}' ({ext}, {file_size} bytes)")
    return clean_name, file_bytes
