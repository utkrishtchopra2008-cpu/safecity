import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';

import { API_BASE_URL, ApiError, requestJson, type CurrentUser } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Surface } from '../components/Surface';

type IncidentDetail = {
  id: string;
  source: { id: string; name: string; source_type: string; status: string };
  event_start_at: string | null;
  event_end_at: string | null;
  received_at: string;
  detector_prediction: {
    category: string;
    label: string | null;
    detector_name: string;
    detector_version: string | null;
    score: number | null;
    score_semantics: string | null;
  };
  review_status: 'unreviewed' | 'reviewed';
  evidence: { id: string; evidence_type: string; status: string; mime_type: string }[];
  reliability_assessments: {
    assessment_version: string;
    assessment_status: string;
    evidence_sufficiency: string | null;
    uncertainty_status: string | null;
    reason_codes: string[];
  }[];
  review_history: { outcome: string; review_note: string | null; reviewed_at: string }[];
};

export function IncidentDetailPage() {
  const { incidentId } = useParams();
  const queryClient = useQueryClient();
  const [reviewNote, setReviewNote] = useState('');
  const [reviewOutcome, setReviewOutcome] = useState<'confirmed' | 'false_alert' | 'inconclusive'>(
    'inconclusive',
  );
  const user = useQuery({
    queryKey: ['current-user'],
    queryFn: () => requestJson<CurrentUser>('/auth/me'),
    retry: false,
  });
  const detail = useQuery({
    queryKey: ['incident', incidentId],
    queryFn: () => requestJson<IncidentDetail>(`/incidents/${incidentId}`),
    enabled: user.isSuccess && Boolean(incidentId),
  });
  const review = useMutation({
    mutationFn: (payload: {
      outcome: 'confirmed' | 'false_alert' | 'inconclusive';
      review_note?: string;
    }) =>
      requestJson(`/incidents/${incidentId}/reviews`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['incident', incidentId] });
      await queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });

  if (user.isLoading) return <p role="status">Checking your session…</p>;
  if (user.error instanceof ApiError && user.error.status === 401)
    return <Navigate to="/login" replace />;
  if (user.isError)
    return (
      <p role="alert">Your session could not be checked. Reload this page or sign in again.</p>
    );
  if (detail.isLoading) return <p role="status">Loading candidate event…</p>;
  if (detail.error instanceof ApiError && detail.error.status === 404)
    return <p role="status">This candidate event is unavailable.</p>;
  if (detail.isError)
    return (
      <Surface>
        <h2>Candidate event could not be loaded</h2>
        <p>{detail.error.message}</p>
      </Surface>
    );
  if (!detail.data) return null;

  const event = detail.data;
  function submitReview(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    review.mutate({
      outcome: reviewOutcome,
      ...(reviewNote.trim() ? { review_note: reviewNote.trim() } : {}),
    });
  }
  return (
    <div className="page-stack">
      <Link to="/incidents">← Candidate events</Link>
      <PageHeader
        eyebrow="Candidate event · review required"
        title={event.detector_prediction.category}
        description="This is a detector observation. It is not a confirmed incident or a finding about a person."
        actions={
          <StatusBadge tone={event.review_status === 'reviewed' ? 'success' : 'warning'}>
            {event.review_status}
          </StatusBadge>
        }
      />
      <div className="detail-grid">
        <Surface>
          <h2>Original detector observation</h2>
          <dl className="detail-list">
            <div>
              <dt>Label</dt>
              <dd>{event.detector_prediction.label ?? 'Not provided'}</dd>
            </div>
            <div>
              <dt>Detector</dt>
              <dd>
                {event.detector_prediction.detector_name}{' '}
                {event.detector_prediction.detector_version ?? ''}
              </dd>
            </div>
            <div>
              <dt>Score</dt>
              <dd>
                {event.detector_prediction.score ?? 'Not provided'}{' '}
                {event.detector_prediction.score_semantics ?? ''}
              </dd>
            </div>
          </dl>
        </Surface>
        <Surface>
          <h2>Evidence</h2>
          {event.evidence.length ? (
            <ul>
              {event.evidence.map((evidence) => (
                <li key={evidence.id}>
                  {evidence.evidence_type} · {evidence.status} · {evidence.mime_type}
                  {evidence.status === 'available' && evidence.evidence_type !== 'frame' ? (
                    <video
                      className="evidence-player"
                      controls
                      preload="metadata"
                      aria-label={`Evidence video ${evidence.id}`}
                      src={`${API_BASE_URL}/evidence/${evidence.id}/content`}
                    />
                  ) : null}
                  {evidence.status === 'available' && evidence.evidence_type === 'frame' ? (
                    <img
                      className="evidence-frame"
                      alt={`Evidence frame ${evidence.id}`}
                      loading="lazy"
                      src={`${API_BASE_URL}/evidence/${evidence.id}/content`}
                    />
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p>No evidence is available to this account for this event.</p>
          )}
        </Surface>
        <Surface>
          <h2>Quality and reliability assessment</h2>
          {event.reliability_assessments.length ? (
            event.reliability_assessments.map((assessment) => (
              <div key={assessment.assessment_version}>
                <p>
                  {assessment.assessment_status} · evidence{' '}
                  {assessment.evidence_sufficiency ?? 'unknown'} · uncertainty{' '}
                  {assessment.uncertainty_status ?? 'unknown'}
                </p>
                {assessment.reason_codes.length ? (
                  <p>Notes: {assessment.reason_codes.join(', ')}</p>
                ) : null}
              </div>
            ))
          ) : (
            <p>No reliability assessment is recorded.</p>
          )}
        </Surface>
        <Surface>
          <h2>Human review</h2>
          {event.review_history.length ? (
            event.review_history.map((review) => (
              <p key={review.reviewed_at}>
                {review.outcome} · {new Date(review.reviewed_at).toLocaleString()}
                {review.review_note ? ` · ${review.review_note}` : ''}
              </p>
            ))
          ) : (
            <p>No human review has been submitted.</p>
          )}
          {event.review_status === 'unreviewed' &&
          ['operator', 'supervisor'].includes(user.data?.role ?? '') ? (
            <form className="form-stack" onSubmit={submitReview}>
              <label>
                Review outcome
                <select
                  value={reviewOutcome}
                  onChange={(event) => setReviewOutcome(event.target.value as typeof reviewOutcome)}
                >
                  <option value="confirmed">Confirmed by reviewer</option>
                  <option value="false_alert">False alert</option>
                  <option value="inconclusive">Inconclusive</option>
                </select>
              </label>
              <label>
                Note (optional)
                <textarea
                  maxLength={2000}
                  value={reviewNote}
                  onChange={(event) => setReviewNote(event.target.value)}
                />
              </label>
              {review.isError ? (
                <p className="form-error" role="alert">
                  {review.error.message}
                </p>
              ) : null}
              {review.isSuccess ? <p role="status">Review saved.</p> : null}
              <button className="button button--primary" type="submit" disabled={review.isPending}>
                {review.isPending ? 'Saving review…' : 'Save review'}
              </button>
            </form>
          ) : null}
        </Surface>
      </div>
    </div>
  );
}
