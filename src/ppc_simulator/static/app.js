function $(id) {
  return document.getElementById(id);
}

function parseClaimsCsv(text) {
  const lines = text.replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  if (lines.length < 2) {
    throw new Error("Claims CSV needs a header row and at least one claim.");
  }
  const headers = lines[0].split(",").map((item) => item.trim());
  return lines.slice(1).map((line, index) => {
    const cols = line.split(",");
    const row = {};
    headers.forEach((header, i) => {
      row[header] = (cols[i] ?? "").trim();
    });
    const required = [
      "claim_id",
      "payer",
      "service_date",
      "submission_date",
      "procedure_code",
      "diagnosis_code",
      "place_of_service",
    ];
    const missing = required.filter((key) => !row[key]);
    if (missing.length) {
      throw new Error(`CSV row ${index + 2} is missing: ${missing.join(", ")}`);
    }
    const auth = (row.authorization_on_file || "false").toLowerCase();
    return {
      claim_id: row.claim_id,
      payer: row.payer,
      service_date: row.service_date,
      submission_date: row.submission_date,
      procedure_code: row.procedure_code,
      diagnosis_code: row.diagnosis_code,
      modifier: row.modifier || null,
      place_of_service: row.place_of_service,
      authorization_on_file: ["1", "true", "yes", "y"].includes(auth),
    };
  });
}

function parsePolicy(text) {
  return JSON.parse(text);
}

function badge(outcome) {
  return `<span class="badge ${outcome}">${outcome.replace("_", " ")}</span>`;
}

function showError(node, err) {
  node.hidden = false;
  node.textContent = err.message || String(err);
}

function hideError(node) {
  node.hidden = true;
  node.textContent = "";
}

async function readApiError(response) {
  const body = await response.text();
  try {
    const parsed = JSON.parse(body);
    if (parsed.detail) {
      return typeof parsed.detail === "string" ? parsed.detail : JSON.stringify(parsed.detail);
    }
  } catch (_err) {
    /* use raw body */
  }
  return body || `Request failed (${response.status})`;
}

async function postJson(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  const type = response.headers.get("content-type") || "";
  if (type.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => {
      item.classList.toggle("is-active", item === button);
      item.setAttribute("aria-selected", item === button ? "true" : "false");
    });
    document.querySelectorAll(".panel").forEach((panel) => {
      panel.classList.toggle("is-active", panel.id === `panel-${button.dataset.tab}`);
    });
  });
});

$("eval-sample").addEventListener("click", async () => {
  hideError($("eval-error"));
  const [policy, claims] = await Promise.all([
    fetch("/fixtures/sample_policy_v1.json").then((r) => r.text()),
    fetch("/fixtures/sample_claims.csv").then((r) => r.text()),
  ]);
  $("eval-policy").value = policy;
  $("eval-claims").value = claims;
});

$("cmp-sample").addEventListener("click", async () => {
  hideError($("cmp-error"));
  const [baseline, proposed, claims] = await Promise.all([
    fetch("/fixtures/sample_policy_v1.json").then((r) => r.text()),
    fetch("/fixtures/sample_policy_v2.json").then((r) => r.text()),
    fetch("/fixtures/sample_claims.csv").then((r) => r.text()),
  ]);
  $("cmp-baseline").value = baseline;
  $("cmp-proposed").value = proposed;
  $("cmp-claims").value = claims;
});

$("evaluate-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError($("eval-error"));
  try {
    const payload = {
      policy: parsePolicy($("eval-policy").value),
      claims: parseClaimsCsv($("eval-claims").value),
    };
    const data = await postJson("/v1/evaluate", payload);
    const counts = data.summary.outcome_counts;
    $("eval-summary").hidden = false;
    $("eval-summary").innerHTML = [
      `<span class="chip">Claims ${data.summary.total_claims}</span>`,
      `<span class="chip">Pass ${counts.pass || 0}</span>`,
      `<span class="chip">Fail ${counts.fail || 0}</span>`,
      `<span class="chip">Manual review ${counts.manual_review || 0}</span>`,
    ].join("");
    const body = $("eval-table").querySelector("tbody");
    body.innerHTML = data.results
      .map((row) => {
        const deciding = (row.traces || []).find((trace) => trace.matched || trace.evaluable === false);
        return `<tr>
          <td>${row.claim_id}</td>
          <td>${badge(row.outcome)}</td>
          <td>${deciding ? deciding.rule_id : ""}</td>
          <td>${(row.explanations || []).join(" ")}</td>
        </tr>`;
      })
      .join("");
    $("eval-table").hidden = false;
    $("eval-export").disabled = false;
    $("eval-export").dataset.payload = JSON.stringify(payload);
  } catch (err) {
    showError($("eval-error"), err);
  }
});

$("eval-export").addEventListener("click", async () => {
  hideError($("eval-error"));
  try {
    const payload = JSON.parse($("eval-export").dataset.payload);
    const csv = await postJson("/v1/evaluate/export", payload);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "evaluation_results.csv";
    link.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    showError($("eval-error"), err);
  }
});

$("compare-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError($("cmp-error"));
  try {
    const data = await postJson("/v2/compare", {
      baseline: parsePolicy($("cmp-baseline").value),
      proposed: parsePolicy($("cmp-proposed").value),
      claims: parseClaimsCsv($("cmp-claims").value),
    });
    const impacts = (data.rule_impacts || [])
      .map((item) => `${item.rule_id} (${item.affected_claim_count})`)
      .join(", ");
    $("cmp-summary").hidden = false;
    $("cmp-summary").innerHTML = [
      `<span class="chip">Changed ${data.changed_claims}</span>`,
      `<span class="chip">Unchanged ${data.unchanged_claims}</span>`,
      `<span class="chip">Impacts ${impacts || "none"}</span>`,
    ].join("");
    const body = $("cmp-table").querySelector("tbody");
    body.innerHTML = data.comparisons
      .map(
        (row) => `<tr>
          <td>${row.claim_id}</td>
          <td>${badge(row.baseline_outcome)}</td>
          <td>${badge(row.proposed_outcome)}</td>
          <td>${row.changed ? "yes" : "no"}</td>
          <td>${(row.attributed_rule_ids || []).join(", ")}</td>
        </tr>`,
      )
      .join("");
    $("cmp-table").hidden = false;
  } catch (err) {
    showError($("cmp-error"), err);
  }
});
