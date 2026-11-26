// Run in the dashboard page as a manager on a disposable demo database.
// The database must have a visible course without feedback (code EMPTY 100).
(async () => {
  const waitFor = async (condition, label) => {
    for (let i = 0; i < 250; i++) {
      if (condition()) return;
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    throw new Error("Timed out: " + label);
  };
  const check = (condition, label) => {
    if (!condition) throw new Error(label);
  };

  await openResponses();
  const initial = rspState.analytics;
  const emptyCourse = rspState.meta.courses.find(course => course.code === "EMPTY 100");
  check(initial?.total > 0 && emptyCourse, "Expected demo feedback and an empty course");
  const filterToEmptyCourse = () => {
    selectManagerView("overview");
    $("mgrKind").value = "course";
    $("mgrKind").dispatchEvent(new Event("change", { bubbles: true }));
    $("mgrTarget").value = "course:" + emptyCourse.id;
    $("mgrTarget").dispatchEvent(new Event("change", { bubbles: true }));
  };

  filterToEmptyCourse();
  await waitFor(() => rspState.trends?.series.length === 0, "empty course trend");
  check(rspState.analytics === initial, "Chart filter preserves overview data");
  check($("mgrTotalFeedback").textContent === String(initial.total), "Chart filter preserves overview KPI");

  selectManagerView("explorer");
  $("rspKindSeg").querySelector('[data-kind="service"]').click();
  await waitFor(() => rspState.data?.items.length && rspState.data.items.every(item => item.kind === "service"), "service feedback");
  check($("mgrTarget").value === "course:" + emptyCourse.id && !rspTarget.value, "Explorer preserves independent chart filters");
  check($("rsTotal").textContent === $("mgrTotalFeedback").textContent, "Explorer and overview use the same type");
  check(rspState.data.items.every(item => item.kind === "service"), "Explorer shows only services");
  const originalFetch = window.fetch;
  const failRequests = (...routes) => {
    window.fetch = (resource, ...args) => routes.some(route => String(resource).includes(route))
      ? Promise.reject(new Error("Simulated request failure"))
      : originalFetch(resource, ...args);
  };
  try {
    failRequests("/evaluations/responses");
    await loadResponses();
    check(rspState.analytics?.total > 0, "Dashboard loads during Explorer failure");
    check($("rsTotal").textContent === "—", "Explorer clears unavailable KPI");
    check($("rspEmpty").textContent.includes("Cannot reach the server"), "Explorer shows its own error");
    check(rspState.trends.series.length === 0, "Trends update despite Explorer failure");

    failRequests("/analytics/overview", "/management/university", "/alerts");
    await loadResponses();
    await waitFor(() => rspState.summary?.total > 0 && !$("rspRefresh").disabled, "successful Summary during Overview failure");
    check($("mgrTotalFeedback").textContent === "—", "Failed Overview clears prior values");
    check($("summaryBody").textContent.includes("average rating"), "Summary renders independently");
    check($("mgrUniversityStats").textContent.includes("unavailable") && !$("mgrDepartmentDetails").textContent,
      "Failed university request clears statistics and department details");
    check($("mgrAlertSummary").textContent.includes("unavailable"), "Alert errors are distinct from empty results");
  } finally {
    window.fetch = originalFetch;
    await loadResponses();
  }
  return "Dashboard browser regressions passed";
})()
