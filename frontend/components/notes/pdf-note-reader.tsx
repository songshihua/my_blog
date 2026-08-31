'use client';

import { useEffect, useRef, useState } from 'react';
import { BookOpenText, Download, ExternalLink, FileImage } from 'lucide-react';
import type {
  PDFDocumentLoadingTask,
  PDFDocumentProxy,
  OnProgressParameters,
  RenderTask,
} from 'pdfjs-dist';

import { NoteDocument } from '@/components/notes/note-document';
import { Spinner } from '@/components/ui/spinner';
import type { ArticleOutlineItem } from '@/lib/site-data';

type ViewMode = 'original' | 'text';

function PdfPage({
  document,
  pageNumber,
}: {
  document: PDFDocumentProxy;
  pageNumber: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [visible, setVisible] = useState(pageNumber <= 2);
  const [width, setWidth] = useState(0);
  const [status, setStatus] = useState<
    'waiting' | 'rendering' | 'ready' | 'error'
  >('waiting');

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && setVisible(true),
      { rootMargin: '900px 0px' },
    );
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(([entry]) => {
      setWidth(Math.max(1, Math.floor(entry.contentRect.width)));
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!visible || !width || !canvasRef.current) return;
    let disposed = false;
    let renderTask: RenderTask | null = null;

    async function renderPage() {
      setStatus('rendering');
      try {
        const page = await document.getPage(pageNumber);
        if (disposed || !canvasRef.current) return;
        const baseViewport = page.getViewport({ scale: 1 });
        const cssScale = width / baseViewport.width;
        const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
        const viewport = page.getViewport({ scale: cssScale * pixelRatio });
        const canvas = canvasRef.current;
        canvas.width = Math.ceil(viewport.width);
        canvas.height = Math.ceil(viewport.height);
        canvas.style.width = `${Math.ceil(viewport.width / pixelRatio)}px`;
        canvas.style.height = `${Math.ceil(viewport.height / pixelRatio)}px`;
        renderTask = page.render({ canvas, viewport });
        await renderTask.promise;
        if (!disposed) setStatus('ready');
        page.cleanup();
      } catch (cause) {
        if (
          !disposed &&
          !(
            cause instanceof Error &&
            cause.name === 'RenderingCancelledException'
          )
        ) {
          setStatus('error');
        }
      }
    }

    void renderPage();
    return () => {
      disposed = true;
      renderTask?.cancel();
    };
  }, [document, pageNumber, visible, width]);

  return (
    <figure className="pdf-page" ref={containerRef}>
      {status !== 'ready' && (
        <div className="pdf-page-placeholder">
          {status === 'error' ? (
            <span>第 {pageNumber} 页渲染失败</span>
          ) : visible ? (
            <span className="inline-flex items-center gap-2">
              <Spinner /> 正在渲染第 {pageNumber} 页
            </span>
          ) : (
            <span>第 {pageNumber} 页</span>
          )}
        </div>
      )}
      <canvas
        aria-label={`PDF 第 ${pageNumber} 页`}
        className={status === 'ready' ? 'block' : 'invisible absolute'}
        ref={canvasRef}
      />
      <figcaption>
        第 {pageNumber} / {document.numPages} 页
      </figcaption>
    </figure>
  );
}

function OriginalPdfView({ filename, url }: { filename: string; url: string }) {
  const [document, setDocument] = useState<PDFDocumentProxy | null>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    let disposed = false;
    let loadingTask: PDFDocumentLoadingTask | null = null;

    async function load() {
      setDocument(null);
      setError('');
      setProgress(0);
      try {
        const pdfjs = await import('pdfjs-dist');
        pdfjs.GlobalWorkerOptions.workerSrc = '/pdfjs/pdf.worker.min.mjs';
        loadingTask = pdfjs.getDocument({
          url,
          cMapUrl: '/pdfjs/cmaps/',
          cMapPacked: true,
          standardFontDataUrl: '/pdfjs/standard_fonts/',
          wasmUrl: '/pdfjs/wasm/',
          iccUrl: '/pdfjs/iccs/',
          enableXfa: true,
        });
        loadingTask.onProgress = ({ loaded, total }: OnProgressParameters) => {
          if (!disposed && total > 0)
            setProgress(Math.round((loaded / total) * 100));
        };
        const loadedDocument = await loadingTask.promise;
        if (!disposed) setDocument(loadedDocument);
      } catch {
        if (!disposed) setError('原版 PDF 加载失败，请下载原文件后查看。');
      }
    }

    void load();
    return () => {
      disposed = true;
      void loadingTask?.destroy();
    };
  }, [url]);

  if (error) {
    return <div className="pdf-viewer-state text-red-700">{error}</div>;
  }
  if (!document) {
    return (
      <div className="pdf-viewer-state">
        <Spinner className="size-5" />
        <span>
          正在加载 {filename}
          {progress ? ` · ${progress}%` : '…'}
        </span>
      </div>
    );
  }

  return (
    <div className="pdf-pages" aria-label={`${filename} 原版视图`}>
      {Array.from({ length: document.numPages }, (_, index) => (
        <PdfPage document={document} key={index + 1} pageNumber={index + 1} />
      ))}
    </div>
  );
}

export function PdfNoteReader({
  downloadUrl,
  filename,
  markdown,
  outline,
  previewUrl,
  title,
}: {
  downloadUrl: string;
  filename: string;
  markdown: string;
  outline: ArticleOutlineItem[];
  previewUrl: string;
  title: string;
}) {
  const [mode, setMode] = useState<ViewMode>('original');

  return (
    <section className="pdf-note-reader">
      <div className="pdf-view-toolbar">
        <div className="pdf-view-tabs" aria-label="PDF 阅读视图">
          <button
            aria-pressed={mode === 'original'}
            className={mode === 'original' ? 'active' : ''}
            onClick={() => setMode('original')}
            type="button"
          >
            <FileImage /> 原版视图
          </button>
          <button
            aria-pressed={mode === 'text'}
            className={mode === 'text' ? 'active' : ''}
            onClick={() => setMode('text')}
            type="button"
          >
            <BookOpenText /> 文本视图
          </button>
        </div>
        <div className="pdf-view-actions">
          <a href={previewUrl} rel="noreferrer" target="_blank">
            <ExternalLink /> 新窗口打开
          </a>
          <a href={downloadUrl}>
            <Download /> 下载
          </a>
        </div>
      </div>

      {mode === 'original' ? (
        <OriginalPdfView filename={filename} url={previewUrl} />
      ) : (
        <NoteDocument markdown={markdown} outline={outline} title={title} />
      )}
    </section>
  );
}
