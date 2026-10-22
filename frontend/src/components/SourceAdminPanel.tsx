import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';

import { ApiError, requestJson } from '../api/client';
import { Surface } from './Surface';

type Source = {
  id: string;
  name: string;
  source_type: string;
};

type UploadAccepted = {
  source_id: string;
  evidence_id: string;
  job_id: string;
  status: string;
};

type JobStatus = {
  status: 'pending' | 'running' | 'completed' | 'failed';
  error_code: string | null;
  result_metadata: Record<string, unknown>;
};

const topics = [
  'weather_advisory',
  'transport_disruption',
  'public_notice',
  'public_event',
  'emergency_advisory',
  'other',
] as const;

export function SourceAdminPanel() {
  const queryClient = useQueryClient();
  const [sourceName, setSourceName] = useState('');
  const [area, setArea] = useState('');
  const [contextEnabled, setContextEnabled] = useState(false);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [videoName, setVideoName] = useState('');
  const [videoFile, setVideoFile] = useState<File>();
  const [jobId, setJobId] = useState<string>();

  const createSource = useMutation({
    mutationFn: () =>
      requestJson<Source>('/sources', {
        method: 'POST',
        body: JSON.stringify({
          name: sourceName,
          source_type: 'simulated',
          context_area_label: area || null,
          context_retrieval_enabled: contextEnabled,
          context_topics: contextEnabled ? selectedTopics : [],
        }),
      }),
    onSuccess: async () => {
      setSourceName('');
      await queryClient.invalidateQueries({ queryKey: ['sources'] });
    },
  });

  const upload = useMutation({
    mutationFn: () => {
      if (!videoFile) throw new Error('Choose a video file first.');
      const body = new FormData();
      body.set('name', videoName);
      body.set('file', videoFile);
      return requestJson<UploadAccepted>('/sources/upload', { method: 'POST', body });
    },
    onSuccess: async (accepted) => {
      setJobId(accepted.job_id);
      setVideoName('');
      setVideoFile(undefined);
      await queryClient.invalidateQueries({ queryKey: ['sources'] });
    },
  });

  const job = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => requestJson<JobStatus>(`/jobs/${jobId}`),
    enabled: Boolean(jobId),
    refetchInterval: (query) =>
      query.state.data?.status === 'pending' || query.state.data?.status === 'running'
        ? 2_000
        : false,
  });

  function submitSimulated(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createSource.mutate();
  }

  function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    upload.mutate();
  }

  const observations = Array.isArray(job.data?.result_metadata.object_observations)
    ? job.data.result_metadata.object_observations.filter(
        (entry): entry is { class_name: string; sample_count: number; mean_score: number } =>
          typeof entry === 'object' &&
          entry !== null &&
          typeof (entry as Record<string, unknown>).class_name === 'string' &&
          typeof (entry as Record<string, unknown>).sample_count === 'number' &&
          typeof (entry as Record<string, unknown>).mean_score === 'number',
      )
    : [];

  return (
    <Surface>
      <h2>Manage video sources</h2>
      <div className="two-column-grid">
        <form className="form-stack" onSubmit={submitSimulated}>
          <h3>Register a simulated source</h3>
          <p>This source is labelled DEMO. It does not connect to a camera or create detections.</p>
          <label htmlFor="source-name">Source name</label>
          <input
            id="source-name"
            value={sourceName}
            onChange={(event) => setSourceName(event.target.value)}
            maxLength={160}
            required
          />
          <label htmlFor="context-area">Approved coarse area for optional public context</label>
          <input
            id="context-area"
            value={area}
            onChange={(event) => setArea(event.target.value)}
            maxLength={160}
            required={contextEnabled}
          />
          <label className="check-field">
            <input
              type="checkbox"
              checked={contextEnabled}
              onChange={(event) => setContextEnabled(event.target.checked)}
            />
            Enable optional public context for this simulated source
          </label>
          {contextEnabled ? (
            <fieldset>
              <legend>Approved context topics</legend>
              {topics.map((topic) => (
                <label className="check-field" key={topic}>
                  <input
                    type="checkbox"
                    checked={selectedTopics.includes(topic)}
                    onChange={(event) =>
                      setSelectedTopics((previous) =>
                        event.target.checked
                          ? [...previous, topic].slice(0, 3)
                          : previous.filter((value) => value !== topic),
                      )
                    }
                  />
                  {topic.replaceAll('_', ' ')}
                </label>
              ))}
            </fieldset>
          ) : null}
          <button
            className="button button--primary"
            disabled={createSource.isPending || (contextEnabled && selectedTopics.length === 0)}
          >
            {createSource.isPending ? 'Registering…' : 'Register simulated source'}
          </button>
          {createSource.isSuccess ? <p role="status">DEMO source registered.</p> : null}
          {createSource.isError ? <p role="alert">{createSource.error.message}</p> : null}
        </form>

        <form className="form-stack" onSubmit={submitUpload}>
          <h3>Upload a prerecorded clip</h3>
          <p>
            Uploads use private Supabase Storage. Local setup must enable storage and configure its
            backend-only credentials first.
          </p>
          <label htmlFor="video-name">Source name</label>
          <input
            id="video-name"
            value={videoName}
            onChange={(event) => setVideoName(event.target.value)}
            maxLength={160}
            required
          />
          <label htmlFor="video-file">Video file</label>
          <input
            id="video-file"
            type="file"
            accept=".mp4,.m4v,.mov,.avi,.mkv,video/mp4,video/quicktime,video/x-msvideo,video/x-matroska"
            required
            onChange={(event) => setVideoFile(event.target.files?.[0])}
          />
          <button className="button button--primary" disabled={upload.isPending}>
            {upload.isPending ? 'Uploading…' : 'Upload and queue processing'}
          </button>
          {upload.isError ? (
            <p role="alert">
              {upload.error instanceof ApiError && upload.error.status === 503
                ? 'Private video storage is not configured for this deployment.'
                : upload.error.message}
            </p>
          ) : null}
          {jobId ? (
            <div aria-live="polite" className="job-result">
              <h4>Processing status: {job.data?.status ?? 'checking'}</h4>
              {job.isError ? <p role="alert">Job status could not be loaded.</p> : null}
              {job.data?.status === 'failed' ? (
                <p role="alert">Processing failed: {job.data.error_code ?? 'unknown error'}.</p>
              ) : null}
              {job.data?.status === 'completed' ? (
                <>
                  <p>Measured video quality and detector observations are reported separately.</p>
                  {typeof job.data.result_metadata.mean_luma_0_255 === 'number' &&
                  typeof job.data.result_metadata.mean_laplacian_variance === 'number' ? (
                    <ul>
                      <li>
                        Mean brightness (luma, 0–255):{' '}
                        {job.data.result_metadata.mean_luma_0_255.toFixed(1)}
                      </li>
                      <li>
                        Mean sharpness observation (Laplacian variance):{' '}
                        {job.data.result_metadata.mean_laplacian_variance.toFixed(1)}
                      </li>
                    </ul>
                  ) : null}
                  {observations.length ? (
                    <ul>
                      {observations.map((observation) => (
                        <li key={observation.class_name}>
                          {observation.class_name}: observed in {observation.sample_count} sampled
                          frames (mean detector score {observation.mean_score.toFixed(2)})
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>No supported object observations were returned for the sampled frames.</p>
                  )}
                  <p>
                    Object observations are not incident classifications. No finding does not mean
                    that no incident occurred. No face images or region coordinates are retained.
                  </p>
                  {job.data.result_metadata.incident_detector === 'not_implemented' ? (
                    <p>Event detection is not configured.</p>
                  ) : null}
                </>
              ) : null}
            </div>
          ) : null}
        </form>
      </div>
    </Surface>
  );
}
