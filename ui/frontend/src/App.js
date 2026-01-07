import React, { useState, useRef } from 'react';
import './App.css';

function App() {
  // Mode: 'home', 'finance', 'graphrag'
  const [mode, setMode] = useState('home');

  // Finance mode state
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tenKData, setTenKData] = useState(null);
  const [loadingTenK, setLoadingTenK] = useState(false);

  // GraphRAG mode state
  const [question, setQuestion] = useState('');
  const [qaLoading, setQaLoading] = useState(false);
  const [qaResult, setQaResult] = useState(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineResult, setPipelineResult] = useState(null);

  // Upload state
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadUseCase, setUploadUseCase] = useState('');
  const fileInputRef = useRef(null);

  const formatNumber = (num) => {
    if (!num) return 'N/A';
    if (num >= 1_000_000_000_000) return `$${(num / 1_000_000_000_000).toFixed(2)}T`;
    if (num >= 1_000_000_000) return `$${(num / 1_000_000_000).toFixed(2)}B`;
    if (num >= 1_000_000) return `$${(num / 1_000_000).toFixed(2)}M`;
    return `$${num.toLocaleString()}`;
  };

  const formatPercentage = (value) => {
    if (!value && value !== 0) return 'N/A';
    return `${(value * 100).toFixed(2)}%`;
  };

  // Finance handlers
  const handleAnalyze = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setTenKData(null);

    try {
      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Analysis failed');
      }

      const result = await response.json();
      setData(result);
      setMode('finance');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze10K = async () => {
    if (!data || !data.ticker) return;
    setLoadingTenK(true);

    try {
      const response = await fetch('http://localhost:5000/api/10k', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: data.ticker, section: 0 }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || '10-K analysis failed');
      }

      const result = await response.json();
      setTenKData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingTenK(false);
    }
  };

  // GraphRAG handlers
  const handleQA = async () => {
    if (!question.trim()) return;
    setQaLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:5000/api/qa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, n_results: 5, include_graph: true }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'QA failed');
      }

      const result = await response.json();
      setQaResult(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setQaLoading(false);
    }
  };

  // File upload handler
  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    setSelectedFiles(files);
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;
    setPipelineLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      selectedFiles.forEach(file => {
        formData.append('files', file);
      });
      formData.append('use_case', uploadUseCase || 'Uploaded documents');

      const response = await fetch('http://localhost:5000/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Upload failed');
      }

      const result = await response.json();
      setPipelineResult(result);
      setSelectedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setPipelineLoading(false);
    }
  };

  const handleKeyPress = (e, handler) => {
    if (e.key === 'Enter') handler();
  };

  const resetToHome = () => {
    setMode('home');
    setData(null);
    setQaResult(null);
    setPipelineResult(null);
    setError(null);
  };

  // HOME SCREEN
  if (mode === 'home') {
    return (
      <div className="App">
        <div className="home-screen">
          <h1 className="main-title">Multi-Agent GraphRAG Builder</h1>
          <p className="subtitle">Analyze financial data or build a knowledge graph from your documents</p>

          <div className="mode-cards">
            <div className="mode-card" onClick={() => setMode('finance')}>
              <h2>Financial Analysis</h2>
              <p>Analyze companies, stock data, and SEC 10-K filings</p>
              <span className="mode-arrow">-&gt;</span>
            </div>

            <div className="mode-card" onClick={() => setMode('graphrag')}>
              <h2>GraphRAG Pipeline</h2>
              <p>Ingest documents, extract entities, and query with AI</p>
              <span className="mode-arrow">-&gt;</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // GRAPHRAG MODE
  if (mode === 'graphrag') {
    return (
      <div className="App">
        <div className="container">
          <button className="back-button" onClick={resetToHome}>
            &lt;- Back to Home
          </button>

          <h1 className="page-title">GraphRAG Pipeline</h1>

          {error && <div className="error">{error}</div>}

          {/* Upload Section */}
          <div className="section">
            <h3>1. Upload Documents</h3>
            <p className="section-desc">Upload your files (PDF, CSV, MD, HTML, JSON, TXT) to build the knowledge graph</p>

            <div className="upload-form">
              <div className="file-input-wrapper">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  multiple
                  accept=".pdf,.csv,.md,.markdown,.html,.htm,.txt,.json"
                  disabled={pipelineLoading}
                />
              </div>

              {selectedFiles.length > 0 && (
                <div className="selected-files">
                  <p>{selectedFiles.length} file(s) selected:</p>
                  <ul>
                    {selectedFiles.map((file, i) => (
                      <li key={i}>{file.name} ({(file.size / 1024).toFixed(1)} KB)</li>
                    ))}
                  </ul>
                </div>
              )}

              <input
                type="text"
                value={uploadUseCase}
                onChange={(e) => setUploadUseCase(e.target.value)}
                placeholder="Use case description (optional)"
                disabled={pipelineLoading}
              />

              <button
                onClick={handleUpload}
                disabled={pipelineLoading || selectedFiles.length === 0}
              >
                {pipelineLoading ? 'Processing...' : 'Upload & Process'}
              </button>
            </div>

            {pipelineResult && (
              <div className="pipeline-result">
                <h4>Pipeline Complete!</h4>
                <div className="stats-grid">
                  <div className="stat">
                    <span className="stat-value">{pipelineResult.files_uploaded?.length || 0}</span>
                    <span className="stat-label">Files</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{pipelineResult.pipeline_stats?.sources_ingested || 0}</span>
                    <span className="stat-label">Ingested</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{pipelineResult.pipeline_stats?.entities_extracted || 0}</span>
                    <span className="stat-label">Entities</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{pipelineResult.pipeline_stats?.relations_extracted || 0}</span>
                    <span className="stat-label">Relations</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">{pipelineResult.pipeline_stats?.documents_indexed || 0}</span>
                    <span className="stat-label">Indexed</span>
                  </div>
                </div>
                <p className="ready-text">Ready for Q&A!</p>
              </div>
            )}
          </div>

          {/* QA Section */}
          <div className="section qa-section">
            <h3>2. Ask Questions (GraphRAG QA)</h3>
            <p className="section-desc">Ask questions about your ingested documents - combines graph + vector search + LLM</p>

            <div className="qa-form">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyPress={(e) => handleKeyPress(e, handleQA)}
                placeholder="Ask a question about your documents..."
                disabled={qaLoading}
              />
              <button onClick={handleQA} disabled={qaLoading || !question.trim()}>
                {qaLoading ? 'Thinking...' : 'Ask'}
              </button>
            </div>

            {qaResult && (
              <div className="qa-result">
                <div className="qa-answer">
                  <h4>Answer</h4>
                  <p>{qaResult.answer}</p>
                </div>

                {qaResult.citations && qaResult.citations.length > 0 && (
                  <div className="qa-citations">
                    <h4>Citations</h4>
                    <ul>
                      {qaResult.citations.map((cite, i) => (
                        <li key={i}>
                          <span className="cite-source">{cite.source}</span>
                          <span className="cite-section">{cite.section}</span>
                          <span className="cite-relevance">{(cite.relevance * 100).toFixed(0)}% relevant</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {qaResult.graph_paths && qaResult.graph_paths.length > 0 && (
                  <div className="qa-paths">
                    <h4>Graph Paths</h4>
                    <ul>
                      {qaResult.graph_paths.map((path, i) => (
                        <li key={i}>
                          {path.source} <span className="path-arrow">-[{path.relation}]-&gt;</span> {path.target}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="qa-sources-info">
                  <span>Vector results: {qaResult.sources?.vector_results || 0}</span>
                  <span>Graph entities: {qaResult.sources?.graph_entities || 0}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // FINANCE MODE (existing functionality)
  return (
    <div className="App">
      <div className="container">
        <button className="back-button" onClick={resetToHome}>
          &lt;- Back to Home
        </button>

        <div className="search-container-top">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => handleKeyPress(e, handleAnalyze)}
            placeholder="Enter company name or ticker..."
            disabled={loading}
          />
          <button onClick={handleAnalyze} disabled={loading}>
            {loading ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>

        {error && <div className="error">{error}</div>}

        {data && (
          <div className="results">
            <div className="header">
              <h2>{data.data.name}</h2>
              <span className="ticker">{data.ticker}</span>
            </div>

            <div className="section">
              <h3>Company Information</h3>
              <div className="grid">
                <div className="metric">
                  <span className="label">Sector</span>
                  <span className="value">{data.data.sector || 'N/A'}</span>
                </div>
                <div className="metric">
                  <span className="label">Industry</span>
                  <span className="value">{data.data.industry || 'N/A'}</span>
                </div>
                <div className="metric">
                  <span className="label">Country</span>
                  <span className="value">{data.data.country || 'N/A'}</span>
                </div>
                <div className="metric">
                  <span className="label">Employees</span>
                  <span className="value">
                    {data.data.employees ? data.data.employees.toLocaleString() : 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            {data.data.description && (
              <div className="section">
                <h3>Business Description</h3>
                <p className="description">{data.data.description}</p>
              </div>
            )}

            <div className="section">
              <h3>Valuation</h3>
              <div className="grid">
                <div className="metric">
                  <span className="label">Current Price</span>
                  <span className="value">
                    {data.data.current_price ? `$${data.data.current_price.toFixed(2)}` : 'N/A'}
                  </span>
                </div>
                <div className="metric">
                  <span className="label">Market Cap</span>
                  <span className="value">{formatNumber(data.data.market_cap)}</span>
                </div>
                <div className="metric">
                  <span className="label">52W High</span>
                  <span className="value">
                    {data.data['52week_high'] ? `$${data.data['52week_high'].toFixed(2)}` : 'N/A'}
                  </span>
                </div>
                <div className="metric">
                  <span className="label">52W Low</span>
                  <span className="value">
                    {data.data['52week_low'] ? `$${data.data['52week_low'].toFixed(2)}` : 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            <div className="section">
              <h3>Revenue & Profitability</h3>
              <div className="grid">
                <div className="metric">
                  <span className="label">Revenue</span>
                  <span className="value">{formatNumber(data.data.revenue)}</span>
                </div>
                <div className="metric">
                  <span className="label">Revenue Growth</span>
                  <span className="value">{formatPercentage(data.data.revenue_growth)}</span>
                </div>
                <div className="metric">
                  <span className="label">EBITDA</span>
                  <span className="value">{formatNumber(data.data.ebitda)}</span>
                </div>
                <div className="metric">
                  <span className="label">Net Income</span>
                  <span className="value">{formatNumber(data.data.net_income)}</span>
                </div>
              </div>
            </div>

            <div className="section">
              <h3>Margins</h3>
              <div className="grid">
                <div className="metric">
                  <span className="label">Profit Margin</span>
                  <span className="value">{formatPercentage(data.data.profit_margin)}</span>
                </div>
                <div className="metric">
                  <span className="label">Operating Margin</span>
                  <span className="value">{formatPercentage(data.data.operating_margin)}</span>
                </div>
                <div className="metric">
                  <span className="label">Gross Margin</span>
                  <span className="value">{formatPercentage(data.data.gross_margin)}</span>
                </div>
                <div className="metric">
                  <span className="label">EBITDA Margin</span>
                  <span className="value">{formatPercentage(data.data.ebitda_margin)}</span>
                </div>
              </div>
            </div>

            <div className="section">
              <h3>Key Ratios</h3>
              <div className="grid">
                <div className="metric">
                  <span className="label">P/E Ratio</span>
                  <span className="value">
                    {data.data.pe_ratio ? data.data.pe_ratio.toFixed(2) : 'N/A'}
                  </span>
                </div>
                <div className="metric">
                  <span className="label">Price/Book</span>
                  <span className="value">
                    {data.data.price_to_book ? data.data.price_to_book.toFixed(2) : 'N/A'}
                  </span>
                </div>
                <div className="metric">
                  <span className="label">Debt/Equity</span>
                  <span className="value">
                    {data.data.debt_to_equity ? data.data.debt_to_equity.toFixed(2) : 'N/A'}
                  </span>
                </div>
                <div className="metric">
                  <span className="label">ROE</span>
                  <span className="value">{formatPercentage(data.data.roe)}</span>
                </div>
              </div>
            </div>

            <div className="section">
              <h3>Analyst Recommendations</h3>
              <div className="grid">
                <div className="metric">
                  <span className="label">Target Price</span>
                  <span className="value">
                    {data.data.target_price ? `$${data.data.target_price.toFixed(2)}` : 'N/A'}
                  </span>
                </div>
                <div className="metric">
                  <span className="label">Recommendation</span>
                  <span className="value">
                    {data.data.recommendation ? data.data.recommendation.replace('_', ' ').toUpperCase() : 'N/A'}
                  </span>
                </div>
                <div className="metric">
                  <span className="label">Number of Analysts</span>
                  <span className="value">{data.data.number_of_analysts || 'N/A'}</span>
                </div>
              </div>
            </div>

            <div className="section">
              <h3>Price History</h3>
              <div className="grid">
                {Object.entries(data.price_history).map(([period, hist]) => {
                  if (hist.error) return null;
                  return (
                    <div key={period} className="metric">
                      <span className="label">
                        {period === '1mo' ? '1 Month' : period === '6mo' ? '6 Months' : '1 Year'}
                      </span>
                      <span className="value">{hist.total_return.toFixed(2)}%</span>
                      <span className="sublabel">
                        Range: ${hist.min_price.toFixed(2)} - ${hist.max_price.toFixed(2)}
                      </span>
                      <span className="sublabel">Volatility: {hist.volatility.toFixed(2)}%</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 10-K SECTION */}
            <div className="section tenk-section">
              <div className="tenk-header">
                <h3>10-K Filing Analysis</h3>
                <button
                  className="tenk-button"
                  onClick={handleAnalyze10K}
                  disabled={loadingTenK}
                >
                  {loadingTenK ? 'Analyzing 10-K...' : tenKData ? 'Refresh 10-K' : 'Analyze 10-K'}
                </button>
              </div>

              {tenKData && tenKData.syntheses && (
                <div className="tenk-results">
                  {tenKData.filing_url && (
                    <div className="filing-link">
                      <a href={tenKData.filing_url} target="_blank" rel="noopener noreferrer">
                        View Original 10-K Filing
                      </a>
                    </div>
                  )}

                  {tenKData.syntheses.business_summary && (
                    <div className="tenk-synthesis">
                      <h4>Business Overview</h4>
                      <p className="synthesis-text">{tenKData.syntheses.business_summary}</p>
                    </div>
                  )}

                  {tenKData.syntheses.risk_summary && (
                    <div className="tenk-synthesis">
                      <h4>Risk Factors</h4>
                      <p className="synthesis-text">{tenKData.syntheses.risk_summary}</p>
                    </div>
                  )}

                  {tenKData.syntheses.mda_summary && (
                    <div className="tenk-synthesis">
                      <h4>Management Discussion & Analysis</h4>
                      <p className="synthesis-text">{tenKData.syntheses.mda_summary}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
