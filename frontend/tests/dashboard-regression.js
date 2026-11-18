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
    $("mgrTarget").value = "course:" + emptyCourse.id;
    $("mgrApplyFilters").click();
  };

  filterToEmptyCourse();
  await waitFor(() => rspState.analytics?.total === 0, "empty course");
  check($("rsTotal").textContent === "0" && $("mgrTotalFeedback").textContent === "0", "Empty course KPI parity");
  check(!rspState.trends.series.length, "Empty course trend");

  selectManagerView("explorer");
  $("rspKindSeg").querySelector('[data-kind="service"]').click();
  await waitFor(() => rspState.analytics?.total > 0, "service feedback");
  check(!$("mgrTarget").value && !rspTarget.value, "Switching type clears incompatible course in both controls");
  check($("rsTotal").textContent === $("mgrTotalFeedback").textContent, "Explorer and overview use the same type");
  check(rspState.data.items.every(item => item.kind === "service"), "Explorer shows only services");
  check(rspState.trends.series.reduce((total, period) => total + period.total, 0) === rspState.analytics.total,
    "Trends use the selected type");

  const originalFetch = window.fetch;
  const failRequests = (...routes) => {
    window.fetch = (resource, ...args) => routes.some(route => String(resource).includes(route))
      ? Promise.reject(new Error("Simulated request failure"))
      : originalFetch(resource, ...args);
  };
  try {
    failRequests("/evaluations/responses");
    filterToEmptyCourse();
    await waitFor(() => rspState.analytics?.total === 0, "successful dashboard during Explorer failure");
    check($("mgrUniversityStats").textContent.includes("0Course reviews"), "University cards update despite Explorer failure");
    check($("rsTotal").textContent === "—", "Explorer clears unavailable KPI");
    check($("rspEmpty").textContent.includes("Cannot reach the server"), "Explorer shows its own error");
    check(rspState.trends.series.length === 0, "Trends update despite Explorer failure");

    failRequests("/analytics/overview", "/management/university", "/alerts");
    $("mgrResetFilters").click();
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
