import { useEffect, useMemo, useState } from 'react'
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js'
import { Bar, Doughnut, Line } from 'react-chartjs-2'
import './App.css'

ChartJS.register(
  ArcElement,
  BarElement,
  CategoryScale,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
)

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

const formatNumber = (value) => {
  if (value === null || value === undefined) return 'n/a'
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(
    value,
  )
}

const formatPercent = (value) => {
  if (value === null || value === undefined) return 'n/a'
  return `${formatNumber(value)}%`
}

const formatBucketLabel = (value) => {
  try {
    const date = new Date(value)
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(date)
  } catch {
    return value
  }
}

function App() {
  const [theme, setTheme] = useState('dark')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [report, setReport] = useState(null)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!file) {
      setError('Select a log file to analyze.')
      return
    }

    setLoading(true)
    setError('')
    setReport(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) {
        throw new Error('Upload failed')
      }
      const data = await response.json()
      setReport(data)
    } catch (err) {
      setError('Unable to analyze the log. Check the API server and try again.')
    } finally {
      setLoading(false)
    }
  }

  const statusChart = useMemo(() => {
    if (!report) return null
    const entries = Object.entries(report.status.counts || {})
    const labels = entries.map(([code]) => code)
    const values = entries.map(([, count]) => count)
    return {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: [
            '#2f4858',
            '#006d77',
            '#83c5be',
            '#ffb703',
            '#fb8500',
            '#e63946',
          ],
          borderWidth: 0,
        },
      ],
    }
  }, [report])

  const errorTrendChart = useMemo(() => {
    if (!report) return null
    const buckets = report.time_buckets || []
    const labels = buckets.map((bucket) =>
      formatBucketLabel(bucket.bucket),
    )
    const values = buckets.map((bucket) =>
      bucket.error_rate === null ? null : bucket.error_rate * 100,
    )
    return {
      labels,
      datasets: [
        {
          label: 'Error rate %',
          data: values,
          borderColor: '#e63946',
          backgroundColor: 'rgba(230, 57, 70, 0.2)',
          fill: true,
          tension: 0.3,
          pointRadius: 2,
        },
      ],
    }
  }, [report])

  const latencyChart = useMemo(() => {
    if (!report) return null
    const endpoints = report.endpoints || []
    const labels = endpoints.map((endpoint) => endpoint.endpoint)
    const values = endpoints.map((endpoint) => endpoint.p95_ms || 0)
    return {
      labels,
      datasets: [
        {
          label: 'p95 latency (ms)',
          data: values,
          backgroundColor: '#006d77',
          borderRadius: 8,
        },
      ],
    }
  }, [report])

  return (
    <div className="page">
      <header className="hero">
        <div className="hero-text">
          <p className="eyebrow">Local analytics workspace</p>
          <div className="hero-heading">
            <h1>Web log intelligence in minutes.</h1>
            <button
              type="button"
              className="theme-toggle"
              onClick={() =>
                setTheme((current) => (current === 'dark' ? 'light' : 'dark'))
              }
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </button>
          </div>
          <p className="subtitle">
            Upload a mixed-format log file and get a full breakdown of status
            distribution, latency percentiles, error bursts, and anomalies.
          </p>
        </div>
        <form className="upload" onSubmit={handleSubmit}>
          <label className="file-drop">
            <input
              type="file"
              accept=".log,.txt,.json"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
            <span>{file ? file.name : 'Choose a log file'}</span>
            <small>Drag and drop also works</small>
          </label>
          <button type="submit" disabled={loading}>
            {loading ? 'Analyzing...' : 'Run analysis'}
          </button>
          <p className="hint">API: {API_BASE}</p>
        </form>
      </header>

      {error && <div className="error">{error}</div>}

      {!report && !loading && (
        <section className="empty-state">
          <div>
            <h2>What you get</h2>
            <ul>
              <li>Status distribution and error rate over time</li>
              <li>Top IPs, slow endpoints, and latency percentiles</li>
              <li>Anomaly counters for malformed or missing fields</li>
            </ul>
          </div>
          <div className="tips">
            <p>
              Tip: Generate a sample log with{' '}
              <code>python scripts/generate_log.py --lines 2000</code>
            </p>
          </div>
        </section>
      )}

      {report && (
        <main className="dashboard">
          <section className="cards">
            <article>
              <h3>Total lines</h3>
              <p>{formatNumber(report.summary.total_lines)}</p>
              <span>Parsed {formatNumber(report.summary.parsed_lines)}</span>
            </article>
            <article>
              <h3>Malformed</h3>
              <p>{formatNumber(report.summary.malformed_lines)}</p>
              <span>Blank {formatNumber(report.summary.blank_lines)}</span>
            </article>
            <article>
              <h3>Error rate</h3>
              <p>
                {formatPercent(
                  report.status.total
                    ? (report.status.error / report.status.total) * 100
                    : null,
                )}
              </p>
              <span>Errors {formatNumber(report.status.error)}</span>
            </article>
            <article>
              <h3>Latency p95</h3>
              <p>{formatNumber(report.duration.percentiles_ms?.p95)}</p>
              <span>Avg {formatNumber(report.duration.avg_ms)} ms</span>
            </article>
          </section>

          <section className="grid">
            <div className="panel">
              <div className="panel-header">
                <h2>Status distribution</h2>
                <p>Total {formatNumber(report.status.total)}</p>
              </div>
              <div className="chart-wrap">
                {statusChart && <Doughnut data={statusChart} />}
              </div>
            </div>
            <div className="panel">
              <div className="panel-header">
                <h2>Error rate over time</h2>
                <p>Bucketed breakdown</p>
              </div>
              <div className="chart-wrap">
                {errorTrendChart && (
                  <Line
                    data={errorTrendChart}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      scales: {
                        y: {
                          ticks: {
                            callback: (value) => `${value}%`,
                          },
                        },
                      },
                    }}
                  />
                )}
              </div>
            </div>
          </section>

          <section className="grid">
            <div className="panel">
              <div className="panel-header">
                <h2>Slow endpoints</h2>
                <p>p95 latency highlights</p>
              </div>
              <div className="chart-wrap">
                {latencyChart && (
                  <Bar
                    data={latencyChart}
                    options={{
                      indexAxis: 'y',
                      responsive: true,
                      maintainAspectRatio: false,
                    }}
                  />
                )}
              </div>
            </div>
            <div className="panel">
              <div className="panel-header">
                <h2>Duration summary</h2>
                <p>Percentiles in milliseconds</p>
              </div>
              <div className="stats">
                <div>
                  <span>p50</span>
                  <strong>{formatNumber(report.duration.percentiles_ms?.p50)}</strong>
                </div>
                <div>
                  <span>p95</span>
                  <strong>{formatNumber(report.duration.percentiles_ms?.p95)}</strong>
                </div>
                <div>
                  <span>p99</span>
                  <strong>{formatNumber(report.duration.percentiles_ms?.p99)}</strong>
                </div>
                <div>
                  <span>Min</span>
                  <strong>{formatNumber(report.duration.min_ms)}</strong>
                </div>
                <div>
                  <span>Max</span>
                  <strong>{formatNumber(report.duration.max_ms)}</strong>
                </div>
                <div>
                  <span>Count</span>
                  <strong>{formatNumber(report.duration.count)}</strong>
                </div>
              </div>
            </div>
          </section>

          <section className="grid">
            <div className="panel">
              <div className="panel-header">
                <h2>Top IPs</h2>
                <p>High traffic sources</p>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>IP</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {report.top_ips.map((ip) => (
                    <tr key={ip.ip}>
                      <td>{ip.ip}</td>
                      <td>{formatNumber(ip.count)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="panel">
              <div className="panel-header">
                <h2>Anomalies</h2>
                <p>Malformed or missing fields</p>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(report.anomalies).map(([type, count]) => (
                    <tr key={type}>
                      <td>{type}</td>
                      <td>{formatNumber(count)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel full-width">
            <div className="panel-header">
              <h2>Endpoint latency table</h2>
              <p>Sorted by p95 latency</p>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Endpoint</th>
                  <th>Count</th>
                  <th>Error rate</th>
                  <th>Avg ms</th>
                  <th>p50</th>
                  <th>p95</th>
                  <th>p99</th>
                </tr>
              </thead>
              <tbody>
                {report.endpoints.map((endpoint) => (
                  <tr key={endpoint.endpoint}>
                    <td>{endpoint.endpoint}</td>
                    <td>{formatNumber(endpoint.count)}</td>
                    <td>
                      {formatPercent(
                        endpoint.error_rate === null
                          ? null
                          : endpoint.error_rate * 100,
                      )}
                    </td>
                    <td>{formatNumber(endpoint.avg_ms)}</td>
                    <td>{formatNumber(endpoint.p50_ms)}</td>
                    <td>{formatNumber(endpoint.p95_ms)}</td>
                    <td>{formatNumber(endpoint.p99_ms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </main>
      )}
    </div>
  )
}

export default App
