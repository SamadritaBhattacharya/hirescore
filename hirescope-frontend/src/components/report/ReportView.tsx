import * as React from "react";
import { ReportHeader } from "@/components/report/ReportHeader";
import { SummaryCard, DetailedAnalysisCard } from "@/components/report/SummaryCards";
import { ScoreBreakdownChart } from "@/components/report/ScoreBreakdownChart";
import { CultureFitCard } from "@/components/report/CultureFitCard";
import { SkillsPanel } from "@/components/report/SkillsPanel";
import { GithubActivityPanel } from "@/components/report/GithubActivityPanel";
import { FlagsPanel } from "@/components/report/FlagsPanel";
import { InterviewQuestions } from "@/components/report/InterviewQuestions";
import { CommunityCard } from "@/components/report/CommunityCard";
import { PartialErrorsNotice } from "@/components/report/PartialErrorsNotice";
import { downloadReportPdf } from "@/lib/api";
import type { FullReport } from "@/types/api";

export function ReportView({ report, onReset }: { report: FullReport; onReset: () => void }) {
  const [exporting, setExporting] = React.useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadReportPdf(report.job_id, report.candidate_name);
    } catch {
      // export failure is non-critical; the report remains visible on screen
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-5">
      <ReportHeader report={report} onExport={handleExport} exporting={exporting} onReset={onReset} />

      <SummaryCard summary={report.executive_summary} />

      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        {report.score_breakdown && <ScoreBreakdownChart breakdown={report.score_breakdown} />}
        <CultureFitCard report={report} />
      </div>

      {report.score_breakdown && <SkillsPanel breakdown={report.score_breakdown} />}

      <div className="grid gap-5 lg:grid-cols-2">
        <GithubActivityPanel report={report} />
        <FlagsPanel greenFlags={report.green_flags} redFlags={report.red_flags} />
      </div>

      <CommunityCard report={report} />

      <InterviewQuestions questions={report.interview_questions} />

      <DetailedAnalysisCard analysis={report.detailed_analysis} />

      <PartialErrorsNotice errors={report.errors} />
    </div>
  );
}
