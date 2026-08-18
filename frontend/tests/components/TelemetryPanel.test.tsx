import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { TelemetryPanel } from '../../src/components/TelemetryPanel';
import type { TelemetryPanelProps } from '../../src/components/TelemetryPanel';
import type { Position } from '../../src/types/iss';

const POSITION: Position = {
  timestamp: '2026-08-17T04:12:09Z',
  latitude: -12.4483,
  longitude: 145.9021,
  altitude_km: 421.7,
  velocity_kmh: 27584.3,
  footprint_radius_km: 2263.1,
  tle_epoch: '2026-08-17T02:30:00Z',
};

function renderPanel(overrides: Partial<TelemetryPanelProps> = {}) {
  return render(
    <TelemetryPanel
      position={POSITION}
      error={null}
      trackError={null}
      isStale={false}
      secondsSinceContact={2}
      pollIntervalMs={3_000}
      {...overrides}
    />,
  );
}

describe('TelemetryPanel', () => {
  it('shows the four telemetry readouts', () => {
    renderPanel();

    expect(screen.getByText('12.4483° S')).toBeInTheDocument();
    expect(screen.getByText('145.9021° E')).toBeInTheDocument();
    expect(screen.getByText('421.7 km')).toBeInTheDocument();
    expect(screen.getByText('27,584 km/h')).toBeInTheDocument();
  });

  it('shows only those four, with no elapsed-time readout', () => {
    const { container } = renderPanel();

    const labels = [...container.querySelectorAll('dt')].map((node) => node.textContent);
    expect(labels).toEqual(['Latitude', 'Longitude', 'Altitude', 'Speed']);
  });

  it('reports tracking while the feed is live', () => {
    renderPanel();

    expect(screen.getByRole('status')).toHaveTextContent('Tracking');
  });

  it('says nothing about elapsed time while the feed is healthy', () => {
    const { container } = renderPanel({ secondsSinceContact: 2 });

    expect(container.querySelector('.telemetry__detail')).toBeEmptyDOMElement();
    expect(screen.queryByText(/ago/)).not.toBeInTheDocument();
  });

  it('says what failed and what happens next', () => {
    renderPanel({
      error: 'Lost contact with the tracking service',
      pollIntervalMs: 15_000,
    });

    expect(screen.getByRole('status')).toHaveTextContent('Reconnecting');
    expect(
      screen.getByText('Lost contact with the tracking service. Retrying in 15s.'),
    ).toBeInTheDocument();
  });

  it('flags a stale signal with the time since last contact', () => {
    renderPanel({ isStale: true, secondsSinceContact: 74 });

    expect(screen.getByRole('status')).toHaveTextContent('Signal stale');
    expect(screen.getByText('Last contact 1m 14s ago.')).toBeInTheDocument();
  });

  it('explains the empty state before the first fix', () => {
    renderPanel({ position: null, secondsSinceContact: null });

    expect(screen.getByRole('status')).toHaveTextContent('Acquiring');
    expect(screen.getAllByText('—')).toHaveLength(4);
  });

  it('shows a key for the two halves of the ground track', () => {
    renderPanel();

    const key = screen.getByRole('list', { name: 'Ground track key' });
    const entries = within(key).getAllByRole('listitem');

    expect(entries.map((entry) => entry.textContent)).toEqual([
      "Where it's going",
      "Where it's been",
    ]);
  });

  it('keeps the key visible before the first fix', () => {
    renderPanel({ position: null, secondsSinceContact: null });

    expect(screen.getByRole('list', { name: 'Ground track key' })).toBeInTheDocument();
  });

  it('surfaces a ground-track failure separately', () => {
    renderPanel({ trackError: 'Could not load the ground track' });

    expect(screen.getByText('Could not load the ground track.')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Tracking');
  });
});
