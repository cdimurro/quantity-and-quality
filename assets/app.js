const ladderRows = [
  ["Electricity or shaft work", 1.0],
  ["Methane, LHV basis", 1.04],
  ["Heat at 150 C, 20 C sink", 0.307],
  ["Heat at 80 C, 20 C sink", 0.17],
  ["Heat at 40 C, 20 C sink", 0.064],
];

function formatFactor(value) {
  return Number(value).toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
}

function renderLadder() {
  const target = document.getElementById("quality-ladder");
  if (!target) return;

  target.innerHTML = ladderRows
    .map(([label, value]) => {
      const width = Math.min(Number(value), 1);
      return `
        <div class="ladder-row">
          <div>
            <div class="ladder-label">${label}</div>
            <div class="track"><span class="fill" style="--value:${width}"></span></div>
          </div>
          <div class="ladder-value">${formatFactor(value)}</div>
        </div>
      `;
    })
    .join("");
}

function thermalFactor(sourceC, sinkC) {
  const sourceK = Number(sourceC) + 273.15;
  const sinkK = Number(sinkC) + 273.15;
  if (!Number.isFinite(sourceK) || !Number.isFinite(sinkK)) {
    throw new Error("Temperatures must be numeric.");
  }
  if (sourceK <= 0 || sinkK <= 0) {
    throw new Error("Temperatures must be above absolute zero.");
  }
  if (sourceK <= sinkK) {
    throw new Error("Source temperature must be greater than sink temperature.");
  }
  return 1 - sinkK / sourceK;
}

function updateCalculator() {
  const output = document.getElementById("calculator-output");
  const sourceC = document.getElementById("source-c").value;
  const sinkC = document.getElementById("sink-c").value;
  const quantity = Number(document.getElementById("quantity").value);
  const unit = document.getElementById("unit").value || "energy unit";

  try {
    const factor = thermalFactor(sourceC, sinkC);
    const exergy = quantity * factor;
    output.textContent = `${quantity} ${unit}, f_X = ${formatFactor(factor)}\naccessible exergy = ${formatFactor(exergy)} ${unit}_ex`;
  } catch (error) {
    output.textContent = error.message;
  }
}

async function loadExamples() {
  const body = document.getElementById("examples-body");
  const filter = document.getElementById("example-filter");
  if (!body || !filter) return;

  const response = await fetch("data/reference_examples.json");
  const examples = await response.json();

  function render() {
    const query = filter.value.trim().toLowerCase();
    const visible = examples.filter((row) => {
      return [row.name, row.category, row.carrier, row.basis, row.reference, row.adoption_note]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });

    body.innerHTML = visible
      .map(
        (row) => `
          <tr>
            <td><strong>${row.name}</strong><br><span>${row.carrier}</span></td>
            <td>${row.category}</td>
            <td>${row.basis}</td>
            <td>${formatFactor(row.exergy_factor)}</td>
            <td>${row.reference}</td>
            <td>${row.adoption_note}</td>
          </tr>
        `
      )
      .join("");
  }

  filter.addEventListener("input", render);
  render();
}

document.addEventListener("DOMContentLoaded", () => {
  renderLadder();
  updateCalculator();
  document.querySelectorAll("#thermal-calculator input").forEach((input) => {
    input.addEventListener("input", updateCalculator);
  });
  loadExamples().catch((error) => {
    const body = document.getElementById("examples-body");
    if (body) {
      body.innerHTML = `<tr><td colspan="6">Could not load examples: ${error.message}</td></tr>`;
    }
  });
});
