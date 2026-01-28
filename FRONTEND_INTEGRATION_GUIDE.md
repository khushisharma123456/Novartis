# Frontend Integration Guide - Quality Agent & Scoring Display

## Patient Detail View - Quality Assessment Section

```html
<!-- Patient Detail Page Enhancement -->

<div class="patient-detail-container">
  <!-- Existing patient info -->
  
  <!-- NEW: QUALITY ASSESSMENT PANEL -->
  <div class="quality-assessment-panel">
    
    <!-- STEP 1: STRENGTH EVALUATION -->
    <div class="strength-section">
      <h3>Case Strength Evaluation</h3>
      
      <div class="strength-badge">
        <span class="strength-level">HIGH</span>
        <span class="strength-score">2/2</span>
      </div>
      
      <div class="strength-breakdown">
        <div class="metric">
          <label>Completeness</label>
          <div class="progress-bar">
            <div class="progress-fill" style="width: 95%">95%</div>
          </div>
        </div>
        
        <div class="metric">
          <label>Temporal Clarity</label>
          <div class="progress-bar">
            <div class="progress-fill" style="width: 85%">85%</div>
          </div>
        </div>
        
        <div class="metric">
          <label>Medical Confirmation</label>
          <div class="progress-bar">
            <div class="progress-fill" style="width: 100%">100%</div>
          </div>
        </div>
        
        <div class="metric">
          <label>Follow-up Responsiveness</label>
          <div class="progress-bar">
            <div class="progress-fill" style="width: 75%">75%</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- STEP 2: CASE SCORE -->
    <div class="scoring-section">
      <h3>Case Score</h3>
      
      <div class="case-score-badge">
        <div class="score-value">-2</div>
        <div class="score-label">Strong Adverse Event</div>
        <div class="confidence">Very High Confidence</div>
      </div>
      
      <div class="score-details">
        <p><strong>Polarity:</strong> Adverse Event (-1)</p>
        <p><strong>Strength:</strong> High (2)</p>
        <p><strong>Calculation:</strong> -1 × 2 = -2</p>
        <p><strong>Interpretation:</strong> Strong Adverse Event - Very High Confidence</p>
      </div>
    </div>
    
    <!-- STEP 3: FOLLOW-UP STATUS -->
    <div class="followup-section">
      <h3>Follow-up Status</h3>
      
      <div class="followup-status">
        <div class="status-item">
          <span class="status-label">Required:</span>
          <span class="status-value">YES</span>
          <span class="status-reason">Weak AE + No Medical Confirmation</span>
        </div>
        
        <div class="status-item">
          <span class="status-label">Sent:</span>
          <span class="status-value">YES</span>
          <span class="status-date">2024-01-28 10:30 AM</span>
        </div>
        
        <div class="status-item">
          <span class="status-label">Response Received:</span>
          <span class="status-value">PENDING</span>
          <span class="status-wait">Waiting for response...</span>
        </div>
      </div>
    </div>
    
    <!-- STEP 4: AI AGENTS -->
    <div class="agents-section">
      <h3>Quality Improvement Agents</h3>
      
      <div class="agents-list">
        
        <!-- Patient Agent -->
        <div class="agent-card active">
          <div class="agent-header">
            <div class="agent-icon">👤</div>
            <div class="agent-info">
              <h4>Patient Symptom Clarity Agent</h4>
              <p class="agent-type">Type: Patient</p>
            </div>
            <span class="agent-status">ACTIVE</span>
          </div>
          
          <div class="agent-questions">
            <p class="questions-count">7 questions pending response</p>
            <ul>
              <li>Can you describe your exact symptoms in detail?</li>
              <li>When exactly did your symptoms start?</li>
              <li>When did your symptoms resolve?</li>
              <li>Did you visit a doctor?</li>
              <li>Any other medications?</li>
              <li>Pre-existing conditions?</li>
              <li>Family history?</li>
            </ul>
          </div>
          
          <button class="btn-view-questions">View & Answer Questions</button>
        </div>
        
        <!-- Doctor Agent -->
        <div class="agent-card active">
          <div class="agent-header">
            <div class="agent-icon">👨‍⚕️</div>
            <div class="agent-info">
              <h4>Doctor Medical Confirmation Agent</h4>
              <p class="agent-type">Type: Doctor</p>
            </div>
            <span class="agent-status">ACTIVE</span>
          </div>
          
          <div class="agent-questions">
            <p class="questions-count">6 questions pending response</p>
            <ul>
              <li>Can you clinically confirm this adverse event?</li>
              <li>What is your professional assessment?</li>
              <li>Relevant medical history?</li>
              <li>Recommended treatment?</li>
              <li>Follow-up recommendation?</li>
              <li>Severity assessment?</li>
            </ul>
          </div>
          
          <button class="btn-view-questions">View & Answer Questions</button>
        </div>
        
        <!-- Hospital Agent -->
        <div class="agent-card completed">
          <div class="agent-header">
            <div class="agent-icon">🏥</div>
            <div class="agent-info">
              <h4>Hospital Clinical Records Agent</h4>
              <p class="agent-type">Type: Hospital</p>
            </div>
            <span class="agent-status">COMPLETED</span>
          </div>
          
          <div class="agent-response">
            <p class="response-label">Response Received:</p>
            <p class="response-date">2024-01-27 3:45 PM</p>
            <p class="response-text">Hospital records confirm adverse event with diagnostic tests showing...</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

---

## KPI Dashboard - Quality Metrics

```html
<!-- Dashboard Page - Quality KPI Section -->

<div class="kpi-dashboard">
  
  <h2>Case Quality Key Performance Indicators</h2>
  
  <!-- OVERVIEW CARDS -->
  <div class="overview-grid">
    <div class="kpi-card">
      <div class="kpi-label">Total Cases</div>
      <div class="kpi-value">150</div>
      <div class="kpi-subtext">Active cases</div>
    </div>
    
    <div class="kpi-card">
      <div class="kpi-label">Cases Evaluated</div>
      <div class="kpi-value">120</div>
      <div class="kpi-subtext">80% assessed</div>
    </div>
    
    <div class="kpi-card">
      <div class="kpi-label">Pending Evaluation</div>
      <div class="kpi-value">30</div>
      <div class="kpi-subtext">20% awaiting assessment</div>
    </div>
  </div>
  
  <!-- STRENGTH DISTRIBUTION -->
  <div class="strength-distribution-section">
    <h3>📊 Case Strength Distribution</h3>
    
    <div class="distribution-grid">
      <!-- STRONG CASES (High) -->
      <div class="strength-card strong">
        <div class="strength-icon">⭐</div>
        <div class="strength-category">STRONG</div>
        <div class="strength-count">85 cases</div>
        <div class="strength-percentage">56.7%</div>
        <div class="strength-description">Score: 2 - High Quality Data</div>
      </div>
      
      <!-- MEDIUM CASES -->
      <div class="strength-card medium">
        <div class="strength-icon">◑</div>
        <div class="strength-category">MEDIUM</div>
        <div class="strength-count">25 cases</div>
        <div class="strength-percentage">16.7%</div>
        <div class="strength-description">Score: 1 - Moderate Quality</div>
      </div>
      
      <!-- WEAK CASES -->
      <div class="strength-card weak">
        <div class="strength-icon">⚠️</div>
        <div class="strength-category">WEAK</div>
        <div class="strength-count">10 cases</div>
        <div class="strength-percentage">6.7%</div>
        <div class="strength-description">Score: 0 - Low Quality/Incomplete</div>
      </div>
      
      <!-- NOT EVALUATED -->
      <div class="strength-card pending">
        <div class="strength-icon">⏳</div>
        <div class="strength-category">PENDING</div>
        <div class="strength-count">30 cases</div>
        <div class="strength-percentage">20%</div>
        <div class="strength-description">Not yet evaluated</div>
      </div>
    </div>
    
    <!-- VISUAL CHART -->
    <div class="strength-chart">
      <canvas id="strengthChart"></canvas>
    </div>
  </div>
  
  <!-- CASE SCORE DISTRIBUTION -->
  <div class="score-distribution-section">
    <h3>📈 Case Score Distribution</h3>
    
    <div class="score-breakdown">
      <div class="score-row">
        <div class="score-label">
          <span class="score-badge score-2">-2</span>
          Strong Adverse Events
        </div>
        <div class="score-bar">
          <div class="score-fill" style="width: 30%"></div>
          <span class="score-count">45 cases</span>
        </div>
      </div>
      
      <div class="score-row">
        <div class="score-label">
          <span class="score-badge score-1">-1</span>
          Weak Adverse Events
        </div>
        <div class="score-bar">
          <div class="score-fill" style="width: 20%"></div>
          <span class="score-count">30 cases</span>
        </div>
      </div>
      
      <div class="score-row">
        <div class="score-label">
          <span class="score-badge score-0">0</span>
          Unclear/Cannot Assess
        </div>
        <div class="score-bar">
          <div class="score-fill" style="width: 3%"></div>
          <span class="score-count">5 cases</span>
        </div>
      </div>
      
      <div class="score-row">
        <div class="score-label">
          <span class="score-badge score-pos-1">+1</span>
          Weak Positive
        </div>
        <div class="score-bar">
          <div class="score-fill" style="width: 10%"></div>
          <span class="score-count">15 cases</span>
        </div>
      </div>
      
      <div class="score-row">
        <div class="score-label">
          <span class="score-badge score-pos-2">+2</span>
          Strong Positive
        </div>
        <div class="score-bar">
          <div class="score-fill" style="width: 37%"></div>
          <span class="score-count">55 cases</span>
        </div>
      </div>
    </div>
  </div>
  
  <!-- FOLLOW-UP STATUS -->
  <div class="followup-status-section">
    <h3>📋 Follow-up Status</h3>
    
    <div class="followup-cards">
      <div class="followup-card">
        <div class="followup-icon">🔔</div>
        <div class="followup-title">Follow-ups Required</div>
        <div class="followup-value">35</div>
        <div class="followup-bar">
          <div class="bar-fill" style="width: 100%; background: #ff6b6b;"></div>
        </div>
      </div>
      
      <div class="followup-card">
        <div class="followup-icon">✉️</div>
        <div class="followup-title">Follow-ups Sent</div>
        <div class="followup-value">28</div>
        <div class="followup-percentage">80% of required</div>
      </div>
      
      <div class="followup-card">
        <div class="followup-icon">✅</div>
        <div class="followup-title">Responses Received</div>
        <div class="followup-value">18</div>
        <div class="followup-percentage">64% of sent</div>
      </div>
      
      <div class="followup-card">
        <div class="followup-icon">⏳</div>
        <div class="followup-title">Pending Responses</div>
        <div class="followup-value">10</div>
        <div class="followup-percentage">36% awaiting response</div>
      </div>
    </div>
  </div>
  
  <!-- QUALITY METRICS -->
  <div class="quality-metrics-section">
    <h3>📊 Quality Metrics</h3>
    
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-label">Average Completeness</div>
        <div class="metric-gauge">
          <div class="gauge-value">78%</div>
          <div class="gauge-label">of required fields</div>
        </div>
      </div>
      
      <div class="metric-card">
        <div class="metric-label">Temporal Clarity</div>
        <div class="metric-gauge">
          <div class="gauge-value">72%</div>
          <div class="gauge-label">clear timeline</div>
        </div>
      </div>
      
      <div class="metric-card">
        <div class="metric-label">Medical Confirmation</div>
        <div class="metric-gauge">
          <div class="gauge-value">65%</div>
          <div class="gauge-label">confirmed cases</div>
        </div>
      </div>
    </div>
  </div>
  
  <!-- QUALITY TREND -->
  <div class="trend-section">
    <h3>📈 Quality Trend</h3>
    
    <div class="trend-info">
      <div class="trend-ratio">
        <h4>Strong vs Weak Ratio</h4>
        <div class="ratio-display">
          <div class="ratio-strong">85 Strong</div>
          <div class="ratio-weak">10 Weak</div>
          <div class="ratio-text">85:10 ratio - GOOD</div>
        </div>
      </div>
      
      <div class="trend-status">
        <h4>Overall Quality Trend</h4>
        <div class="trend-badge improving">
          ↗️ IMPROVING
        </div>
        <p>Quality improving steadily with increased completeness</p>
      </div>
    </div>
  </div>
</div>
```

---

## CSS Styling Guide

```css
/* STRENGTH BADGES */
.strength-badge {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  color: white;
}

.strength-level {
  font-size: 1.5rem;
  font-weight: bold;
}

.strength-score {
  font-size: 2rem;
  font-weight: bold;
}

/* CASE SCORE BADGES */
.case-score-badge {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  padding: 2rem;
  border-radius: 8px;
  text-align: center;
}

.score-value {
  font-size: 3rem;
  font-weight: bold;
}

.score-label {
  font-size: 1.2rem;
  margin-top: 0.5rem;
}

.confidence {
  font-size: 0.9rem;
  margin-top: 0.5rem;
  opacity: 0.9;
}

/* KPI CARDS */
.kpi-card {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  text-align: center;
}

.kpi-value {
  font-size: 2.5rem;
  font-weight: bold;
  color: #667eea;
  margin: 1rem 0;
}

/* STRENGTH CARDS */
.strength-card {
  padding: 1.5rem;
  border-radius: 8px;
  text-align: center;
  color: white;
}

.strength-card.strong {
  background: linear-gradient(135deg, #34d399 0%, #10b981 100%);
}

.strength-card.medium {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
}

.strength-card.weak {
  background: linear-gradient(135deg, #f87171 0%, #ef4444 100%);
}

.strength-card.pending {
  background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
}

.strength-count {
  font-size: 2rem;
  font-weight: bold;
  margin: 0.5rem 0;
}

/* AGENT CARDS */
.agent-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  background: white;
}

.agent-card.active {
  border-color: #667eea;
  background: #f0f4ff;
}

.agent-card.completed {
  border-color: #34d399;
  background: #f0fdf4;
}

.agent-status {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: bold;
}

/* PROGRESS BARS */
.progress-bar {
  background: #e5e7eb;
  border-radius: 999px;
  height: 0.5rem;
  overflow: hidden;
}

.progress-fill {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  color: white;
  font-size: 0.75rem;
  padding-right: 0.5rem;
}
```

---

## Integration Checklist

- [ ] Add strength evaluation scores to patient detail page
- [ ] Display case score badge prominently
- [ ] Show follow-up status with clear indicators
- [ ] Create agent question view/response form
- [ ] Build KPI dashboard with charts
- [ ] Add strength distribution visualization
- [ ] Create case score distribution chart
- [ ] Show quality metrics gauges
- [ ] Add real-time updates for agent responses
- [ ] Create notifications for quality alerts

---

## JavaScript Integration Example

```javascript
// Fetch and display KPI dashboard
async function loadKPIDashboard() {
  const response = await fetch('/api/dashboard/kpi');
  const data = await response.json();
  
  // Update strength distribution
  updateStrengthChart(data.strength_distribution);
  
  // Update case scores
  updateScoreDistribution(data.case_score_distribution);
  
  // Update follow-up status
  updateFollowupStatus(data.followup_status);
  
  // Show key metrics
  displayQualityMetrics(data.quality_metrics);
}

// Load case details with quality assessment
async function loadCaseDetails(caseId) {
  const response = await fetch(`/api/dashboard/case-details/${caseId}`);
  const data = await response.json();
  
  // Display strength evaluation
  displayStrengthEvaluation(data.strength_evaluation);
  
  // Display case score
  displayCaseScore(data.case_scoring);
  
  // Display agents
  displayAgents(data.agents);
  
  // Display follow-ups
  displayFollowups(data.followup);
}
```

This provides a complete UI/UX implementation guide for displaying all quality metrics!
