import type { Position } from '../types/iss';
import { formatAltitude, formatLatitude, formatLongitude, formatSpeed } from '../utils/coordinates';
import { formatElapsed } from '../utils/time';

const NO_VALUE = '—';

type Condition = 'tracking' | 'acquiring' | 'stale' | 'reconnecting';

interface Status {
  condition: Condition;
  label: string;
  detail: string;
}

function describeStatus(props: TelemetryPanelProps): Status {
  const retryInSeconds = Math.round(props.pollIntervalMs / 1000);

  if (props.error !== null) {
    return {
      condition: 'reconnecting',
      label: 'Reconnecting',
      detail: `${props.error}. Retrying in ${String(retryInSeconds)}s.`,
    };
  }

  if (props.position === null) {
    return {
      condition: 'acquiring',
      label: 'Acquiring',
      detail: 'Waiting for the first fix from the tracking service.',
    };
  }

  if (props.isStale && props.secondsSinceContact !== null) {
    return {
      condition: 'stale',
      label: 'Signal stale',
      detail: `Last contact ${formatElapsed(props.secondsSinceContact)} ago.`,
    };
  }

  // Nothing to say while the feed is healthy; the beacon already reports it.
  return { condition: 'tracking', label: 'Tracking', detail: '' };
}

function Readout({ label, value }: { label: string; value: string }): React.JSX.Element {
  return (
    <div className="telemetry__readout">
      <dt className="telemetry__label">{label}</dt>
      <dd className="telemetry__value">{value}</dd>
    </div>
  );
}

function KeyEntry({
  variant,
  label,
}: {
  variant: 'past' | 'future';
  label: string;
}): React.JSX.Element {
  return (
    <li className="telemetry__key-entry">
      {/* The swatch sits on the basemap's own land colour, so each line reads here
          exactly as it does on the map. */}
      <span className="telemetry__key-swatch" aria-hidden="true">
        <span className={`telemetry__key-line telemetry__key-line--${variant}`} />
      </span>
      {label}
    </li>
  );
}

export interface TelemetryPanelProps {
  position: Position | null;
  error: string | null;
  trackError: string | null;
  isStale: boolean;
  secondsSinceContact: number | null;
  pollIntervalMs: number;
}

export function TelemetryPanel(props: TelemetryPanelProps): React.JSX.Element {
  const { position, trackError } = props;
  const status = describeStatus(props);

  return (
    <header className="telemetry" aria-label="ISS telemetry">
      <div className="telemetry__identity">
        <h1 className="telemetry__title">ISS</h1>
        <p className={`telemetry__status telemetry__status--${status.condition}`} role="status">
          <span className="telemetry__beacon" aria-hidden="true" />
          {status.label}
        </p>
      </div>

      <dl className="telemetry__grid">
        <Readout
          label="Latitude"
          value={position === null ? NO_VALUE : formatLatitude(position.latitude)}
        />
        <Readout
          label="Longitude"
          value={position === null ? NO_VALUE : formatLongitude(position.longitude)}
        />
        <Readout
          label="Altitude"
          value={position === null ? NO_VALUE : formatAltitude(position.altitude_km)}
        />
        <Readout
          label="Speed"
          value={position === null ? NO_VALUE : formatSpeed(position.velocity_kmh)}
        />
      </dl>

      <ul className="telemetry__key" aria-label="Ground track key">
        <KeyEntry variant="future" label="Where it's going" />
        <KeyEntry variant="past" label="Where it's been" />
      </ul>

      {/* Always in the DOM so the live region can announce; CSS collapses it when empty,
          which is the healthy case. Takes a full row of its own when it does appear. */}
      <p className="telemetry__detail" aria-live="polite">
        {status.detail}
      </p>
      {trackError !== null && (
        <p className="telemetry__detail telemetry__detail--warn">{trackError}.</p>
      )}
    </header>
  );
}
