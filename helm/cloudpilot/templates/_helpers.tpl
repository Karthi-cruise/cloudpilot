{{/*
Expand the name of the chart.
*/}}
{{- define "cloudpilot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this.
If release name contains chart name it will be used as a full name.
*/}}
{{- define "cloudpilot.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart label.
*/}}
{{- define "cloudpilot.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "cloudpilot.labels" -}}
helm.sh/chart: {{ include "cloudpilot.chart" . }}
{{ include "cloudpilot.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: cloudpilot
team: platform-engineering
{{- end }}

{{/*
Selector labels
*/}}
{{- define "cloudpilot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cloudpilot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app: {{ include "cloudpilot.name" . }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "cloudpilot.serviceAccountName" -}}
{{- printf "%s-sa" (include "cloudpilot.fullname" .) }}
{{- end }}

{{/*
Create the image tag — falls back to chart appVersion
*/}}
{{- define "cloudpilot.imageTag" -}}
{{- .Values.image.tag | default .Chart.AppVersion }}
{{- end }}
