// eda.js

Chart.defaults.color = '#475467';
Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(16, 24, 40, 0.95)';
Chart.defaults.plugins.tooltip.titleFont = { size: 13, weight: '700' };
Chart.defaults.plugins.tooltip.bodyFont = { size: 13 };
Chart.defaults.plugins.tooltip.padding = 12;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.tooltip.borderColor = 'rgba(208, 213, 221, 0.4)';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.displayColors = false;

async function initDashboard() {
  try {
    const [cases] = await Promise.all([
      getCases(),
      new Promise(r => setTimeout(r, 800))
    ]);
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';
    
    populateStats(cases);
    renderRiskDist(cases);
    renderTierBreakdown(cases);
    renderMccRisk(cases);
    renderTopDrivers(cases);
    renderFraudBreakdown(cases);
  } catch(err) {
    document.getElementById('loading-state').innerHTML = `<span class="error-text">Failed to load data: ${err.message}</span>`;
  }
}

function populateStats(cases) {
  try {
    document.getElementById('stat-total-merchants').textContent = cases.length.toLocaleString();
    const highRisk = cases.filter(c => c.risk_score > 0.70).length;
    document.getElementById('stat-avg-risk').textContent = highRisk.toLocaleString();
    
    const mccData = {};
    let totalResolved = 0;
    let totalFraud = 0;

    cases.forEach(c => {
      const mcc = c.mcc_category || 'unknown';
      if (!mccData[mcc]) mccData[mcc] = { sum: 0, count: 0 };
      mccData[mcc].sum += c.risk_score || 0;
      mccData[mcc].count++;

      if (c.ground_truth_label === 'fraud') totalFraud++;
      if (c.ground_truth_label === 'fraud' || c.ground_truth_label === 'legitimate') totalResolved++;
    });
    
    if (Object.keys(mccData).length > 0) {
      const topMcc = Object.keys(mccData).sort((a,b) => (mccData[b].sum/mccData[b].count) - (mccData[a].sum/mccData[a].count))[0];
      document.getElementById('stat-top-category').textContent = topMcc.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    } else {
      document.getElementById('stat-top-category').textContent = 'N/A';
    }

    const fraudRate = totalResolved > 0 ? ((totalFraud / totalResolved) * 100).toFixed(1) + '%' : 'N/A';
    document.getElementById('stat-fraud-rate').textContent = fraudRate;
  } catch(e) {
    console.error("Error in populateStats:", e);
  }
}

function renderTopDrivers(cases) {
  try {
    const ctx = document.getElementById('chart-top-drivers').getContext('2d');
    const drivers = {};
    
    cases.forEach(c => {
      if (c.risk_score > 0.70 && Array.isArray(c.top_reasons)) {
        c.top_reasons.forEach(r => {
          if (r && r.direction === 'raises risk') {
            const label = r.friendly_label || r.feature || 'Unknown';
            if (!drivers[label]) drivers[label] = 0;
            drivers[label] += (r.impact || 0);
          }
        });
      }
    });
    
    const sorted = Object.keys(drivers).sort((a,b) => drivers[b] - drivers[a]).slice(0, 5);
    const data = sorted.map(d => drivers[d]);
    
    // If no data, show a message
    if (sorted.length === 0) {
      sorted.push('No High Risk Drivers Found');
      data.push(0);
    }
    
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: sorted,
        datasets: [{
          label: 'Aggregated SHAP Impact',
          data: data,
          backgroundColor: '#2F5BFF', // Changed to accent blurple
          borderRadius: 4,
          barPercentage: 0.6,
          categoryPercentage: 0.8
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, grid: { color: 'rgba(16,24,40,0.04)', drawBorder: false } },
          y: { grid: { display: false, drawBorder: false } }
        }
      }
    });
  } catch (e) {
    console.error("Error in renderTopDrivers:", e);
    document.getElementById('chart-top-drivers').parentElement.innerHTML = '<div style="color:red; padding: 20px;">Error rendering chart: ' + e.message + '</div>';
  }
}

function renderFraudBreakdown(cases) {
  try {
    const ctx = document.getElementById('chart-fraud-breakdown').getContext('2d');
    let fraud = 0; let legitimate = 0; let unresolved = 0;
    
    cases.forEach(c => {
      if (c.ground_truth_label === 'fraud') fraud++;
      else if (c.ground_truth_label === 'legitimate') legitimate++;
      else unresolved++;
    });
    
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Fraud', 'Legitimate', 'Unresolved'],
        datasets: [{
          data: [fraud, legitimate, unresolved],
          backgroundColor: ['#F04438', '#12B76A', '#D0D5DD'],
          borderRadius: 6,
          barPercentage: 0.5,
          categoryPercentage: 0.7
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: 'rgba(16,24,40,0.04)', drawBorder: false } },
          x: { grid: { display: false, drawBorder: false } }
        }
      }
    });
  } catch (e) {
    console.error("Error in renderFraudBreakdown:", e);
  }
}

function renderRiskDist(cases) {
  try {
    const ctx = document.getElementById('chart-risk-dist').getContext('2d');
    const bins = new Array(10).fill(0);
    cases.forEach(c => {
      let pct = (c.risk_score || 0) * 100;
      if (pct >= 100) pct = 99.9;
      bins[Math.floor(pct / 10)]++;
    });
    
    const labels = bins.map((_, i) => `${i*10}-${i*10+10}%`);
    
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Merchants',
          data: bins,
          backgroundColor: '#2F5BFF',
          borderRadius: 4,
          barPercentage: 0.7,
          categoryPercentage: 0.9
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: 'rgba(16,24,40,0.04)', drawBorder: false } },
          x: { grid: { display: false, drawBorder: false } }
        }
      }
    });
  } catch (e) {
    console.error("Error in renderRiskDist:", e);
  }
}

function renderTierBreakdown(cases) {
  try {
    const ctx = document.getElementById('chart-tier-breakdown').getContext('2d');
    let autoClear = 0; let agentReview = 0; let escalate = 0;
    
    cases.forEach(c => {
      if (c.decision_tier === 'auto_clear') autoClear++;
      else if (c.decision_tier === 'agent_review') agentReview++;
      else if (c.decision_tier === 'escalate') escalate++;
    });
    
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Auto Clear', 'Agent Review', 'Escalate'],
        datasets: [{
          data: [autoClear, agentReview, escalate],
          backgroundColor: ['#12B76A', '#F79009', '#F04438'],
          borderWidth: 2,
          borderColor: '#FFFFFF',
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '75%',
        plugins: {
          legend: { position: 'bottom', labels: { color: '#475467', padding: 20, usePointStyle: true, font: {weight: '500'} } }
        }
      }
    });
  } catch (e) {
    console.error("Error in renderTierBreakdown:", e);
  }
}

function renderMccRisk(cases) {
  try {
    const ctx = document.getElementById('chart-mcc-risk').getContext('2d');
    const mccData = {};
    cases.forEach(c => {
      const mcc = c.mcc_category || 'unknown';
      if (!mccData[mcc]) mccData[mcc] = { sum: 0, count: 0 };
      mccData[mcc].sum += (c.risk_score || 0);
      mccData[mcc].count++;
    });
    
    const mccs = Object.keys(mccData).sort((a,b) => (mccData[b].sum/mccData[b].count) - (mccData[a].sum/mccData[a].count));
    const labels = mccs.map(m => m.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()));
    
    // Explicitly convert to Numbers here
    const avgScores = mccs.map(m => Number((mccData[m].sum / mccData[m].count * 100).toFixed(1)));
    
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Average Risk Score (%)',
          data: avgScores,
          backgroundColor: avgScores.map(score => score > 70 ? '#F04438' : (score > 20 ? '#F79009' : '#12B76A')),
          borderRadius: 4,
          barPercentage: 0.6,
          categoryPercentage: 0.8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, max: 100, grid: { color: 'rgba(16,24,40,0.04)', drawBorder: false } },
          x: { grid: { display: false, drawBorder: false }, ticks: { autoSkip: false, maxRotation: 45, minRotation: 45, font: {size: 11} } }
        }
      }
    });
  } catch (e) {
    console.error("Error in renderMccRisk:", e);
    document.getElementById('chart-mcc-risk').parentElement.innerHTML = '<div style="color:red; padding: 20px;">Error rendering chart: ' + e.message + '</div>';
  }
}

initDashboard();
