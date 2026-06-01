import { useEffect, useRef, useState } from 'react';
import { deleteMemo, getContentDetail, getReflectionQuestions, saveMemo } from '../../api/endpoints';
import type { Content } from '../../types';
import SlideDrawer from '../ui/SlideDrawer';
import styles from './ContentDrawer.module.css';

const MEMO_MAX = 500;

interface ContentDrawerProps {
  contentId: number | null;
  onClose: () => void;
}

export default function ContentDrawer({ contentId, onClose }: ContentDrawerProps) {
  const [detail, setDetail] = useState<Content | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [questions, setQuestions] = useState<string[]>([]);
  const [questionsLoading, setQuestionsLoading] = useState(false);
  const [memoText, setMemoText] = useState('');
  const [isSavingMemo, setIsSavingMemo] = useState(false);
  const [memoSaved, setMemoSaved] = useState(false);
  const memoSavedTimerRef = useRef<number | null>(null);
  const isOpen = contentId !== null;

  useEffect(() => {
    if (contentId === null) {
      setDetail(null);
      setQuestions([]);
      setMemoText('');
      setMemoSaved(false);
      return;
    }

    const controller = new AbortController();
    const { signal } = controller;

    setIsLoading(true);
    setQuestionsLoading(true);
    setQuestions([]);
    setMemoText('');
    setMemoSaved(false);

    void getContentDetail(contentId)
      .then((data) => {
        if (!signal.aborted) {
          setDetail(data);
          setMemoText(data.memo ?? '');
        }
      })
      .finally(() => { if (!signal.aborted) setIsLoading(false); });

    void getReflectionQuestions(contentId, signal)
      .then((qs) => { if (!signal.aborted) setQuestions(qs); })
      .catch(() => { if (!signal.aborted) setQuestions([]); })
      .finally(() => { if (!signal.aborted) setQuestionsLoading(false); });

    return () => {
      controller.abort();
      if (memoSavedTimerRef.current !== null) window.clearTimeout(memoSavedTimerRef.current);
    };
  }, [contentId]);

  const handleSaveMemo = async () => {
    if (!contentId || !memoText.trim()) return;
    setIsSavingMemo(true);
    try {
      await saveMemo(contentId, memoText.trim());
      setMemoSaved(true);
      if (memoSavedTimerRef.current !== null) window.clearTimeout(memoSavedTimerRef.current);
      memoSavedTimerRef.current = window.setTimeout(() => setMemoSaved(false), 2000);
    } catch {
      alert('Failed to save. Please check your network connection.');
    } finally {
      setIsSavingMemo(false);
    }
  };

  const handleDeleteMemo = async () => {
    if (!contentId) return;
    setIsSavingMemo(true);
    try {
      await deleteMemo(contentId);
      setMemoText('');
      setMemoSaved(false);
    } catch {
      alert('Failed to save. Please check your network connection.');
    } finally {
      setIsSavingMemo(false);
    }
  };

  return (
    <SlideDrawer
      title={detail?.title || 'Content detail'}
      subtitle={detail?.platform || 'Context and metadata'}
      isOpen={isOpen}
      onClose={onClose}
    >
      {isLoading ? <p>Loading detail…</p> : null}
      {detail ? (
        <>
          {detail.thumbnail_url ? (
            <img
              src={detail.thumbnail_url}
              alt=""
              className={styles.hero}
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
            />
          ) : null}

          <section className={styles.section}>
            <h3>Summary</h3>
            <p>{detail.summary || 'No summary is available yet for this item.'}</p>
          </section>

          <section className={styles.section}>
            <h3>Metadata</h3>
            <dl className={styles.metaList}>
              <div><dt>Status</dt><dd>{detail.status}</dd></div>
              <div><dt>Type</dt><dd>{detail.content_type}</dd></div>
              <div><dt>Author</dt><dd>{detail.author || 'N/A'}</dd></div>
              <div><dt>Created</dt><dd>{new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(detail.created_at))}</dd></div>
            </dl>
          </section>

          {detail.auto_tag_category ? (
            <section className={styles.section}>
              <h3>Auto-tag</h3>
              <dl className={styles.metaList}>
                <div><dt>Category</dt><dd>{detail.auto_tag_category}</dd></div>
                {detail.auto_tag_keywords_en?.length > 0 ? (
                  <div><dt>Keywords</dt><dd>{detail.auto_tag_keywords_en.join(', ')}</dd></div>
                ) : null}
              </dl>
            </section>
          ) : null}

          {questionsLoading ? (
            <section className={styles.section}>
              <h3>Reflection questions</h3>
              <p className={styles.loadingText}>Generating questions…</p>
            </section>
          ) : questions.length > 0 ? (
            <section className={styles.section}>
              <h3>Reflection questions</h3>
              <ul className={styles.questionList}>
                {questions.map((q, i) => (
                  <li key={i} className={styles.questionPill}>{q}</li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className={styles.section}>
            <h3>Memo</h3>
            <textarea
              className={styles.memoTextarea}
              placeholder="What did you think about this?"
              value={memoText}
              onChange={(e) => {
                if (e.target.value.length <= MEMO_MAX) setMemoText(e.target.value);
              }}
              rows={4}
              disabled={isSavingMemo}
            />
            <div className={styles.memoFooter}>
              <span className={`${styles.memoCounter} ${memoText.length >= MEMO_MAX ? styles.memoCounterLimit : ''}`}>
                {memoText.length} / {MEMO_MAX}
              </span>
              <div className={styles.memoActions}>
                {memoText.trim() && (
                  <button
                    type="button"
                    className={styles.memoDeleteBtn}
                    onClick={() => void handleDeleteMemo()}
                    disabled={isSavingMemo}
                  >
                    Delete
                  </button>
                )}
                <button
                  type="button"
                  className={`${styles.memoSaveBtn} ${memoSaved ? styles.memoSaveBtnSaved : ''}`}
                  onClick={() => void handleSaveMemo()}
                  disabled={isSavingMemo || !memoText.trim()}
                >
                  {memoSaved ? 'Saved ✓' : isSavingMemo ? 'Saving…' : 'Save'}
                </button>
              </div>
            </div>
          </section>

          <section className={styles.section}>
            <h3>Source</h3>
            <a href={detail.url} target="_blank" rel="noreferrer">Open original content</a>
          </section>
        </>
      ) : null}
    </SlideDrawer>
  );
}
