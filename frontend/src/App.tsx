import { AppFooter, AppHeader, AppHero, ResolverPanel } from "./components/AppChrome";
import { useTranslation } from "react-i18next";
import { AuthPanel } from "./components/AuthPanel";
import { DownloadPanel } from "./components/DownloadPanel";
import { JobList } from "./components/JobList";
import { ResourcePreview } from "./components/ResourcePreview";
import { VideoPreview } from "./components/VideoPreview";
import { useAppController } from "./hooks/useAppController";

export function App() {
  const controller = useAppController();
  const { t } = useTranslation();

  if (!controller.hasSession) {
    return <main className="fatal-state"><h1>{t("app.invalidSessionTitle")}</h1><p>{t("app.invalidSessionText")}</p></main>;
  }

  if (controller.shuttingDown) {
    return <main className="fatal-state"><h1>{t("app.shutdownTitle")}</h1><p>{t("app.shutdownText")}</p></main>;
  }

  return (
    <main className="app-shell">
      <AppHeader status={controller.status} onQuit={() => void controller.handleQuit()} />
      <AppHero />

      <AuthPanel
        api={controller.api}
        auth={controller.auth}
        authStatus={controller.authStatus}
        checking={controller.authChecking}
        checkError={controller.authCheckError}
        autoSelected={controller.autoSelected}
        onRefresh={() => controller.setAuthCheckNonce((value) => value + 1)}
        onChange={controller.handleAuthChange}
        disabled={controller.resolving || controller.authInitializing}
      />

      <ResolverPanel
        credential={controller.credential}
        error={controller.error}
        resolving={controller.resolving}
        onCredentialChange={controller.setCredential}
        onSubmit={(event) => void controller.handleResolve(event)}
      />
      {controller.idleWarningMinutes !== null && (
        <div className="warning-banner" role="status">
          {t("app.idleWarning", { minutes: controller.idleWarningMinutes })}
        </div>
      )}

      {controller.video && (
        <VideoPreview
          video={controller.video}
          selectedPages={controller.selectedPages}
          onSelectedPagesChange={controller.setSelectedPages}
        />
      )}
      {controller.resource && !controller.video && (
        <ResourcePreview
          resource={controller.resource}
          selectedItems={controller.selectedItems}
          onSelectedItemsChange={controller.setSelectedItems}
        />
      )}
      {controller.resource && controller.status && (
        <DownloadPanel
          status={controller.status}
          outputDir={controller.outputDir}
          onOutputDirChange={controller.setOutputDir}
          qualities={controller.commonQualities}
          qualityId={controller.qualityId}
          onQualityIdChange={controller.setQualityId}
          videoMode={controller.videoMode}
          onVideoModeChange={controller.setVideoMode}
          audioFormat={controller.audioFormat}
          onAudioFormatChange={controller.setAudioFormat}
          selectedCount={
            controller.video
              ? controller.selectedPages.size
              : controller.selectedItems.size
          }
          hasExactQualities={Boolean(controller.video)}
          qualityHeight={controller.qualityHeight}
          onQualityHeightChange={controller.setQualityHeight}
          busy={controller.creating}
          onCreate={(kind) => void controller.handleCreate(kind)}
          onOpenOutput={() => void controller.handleOpenOutput()}
        />
      )}
      <JobList
        jobs={controller.jobs}
        onCancel={(id) => void controller.handleCancel(id)}
        onRetry={(id) => void controller.handleRetry(id)}
      />

      <AppFooter status={controller.status} />
    </main>
  );
}
