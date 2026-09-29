# Contributing to the Prairie Plugin Catalog

The [Prairie contribution guide](https://github.com/prairie-server/prairie-server/blob/main/CONTRIBUTING.md)
covers project-wide coordination, focused changes, evidence, AI disclosure, and
pull request expectations. Those requirements apply here; this guide adds the
catalog-specific workflow.

## Before you start

Open an [issue](https://github.com/prairie-server/prairie-plugins/issues) before
changing catalog schema, provenance rules, release ingestion, or automation.
Plugin implementation changes belong in the individual plugin repository;
plugin contract changes belong in
[`prairie-plugin-sdk`](https://github.com/prairie-server/prairie-plugin-sdk).

Release entries are normally generated from a plugin's published GitHub release
by the catalog workflows. Do not hand-edit checksums or release metadata to work
around a missing or incorrect upstream artifact.

## Development setup

Use the Go version declared in `go.mod`. The update command reads release assets
from GitHub, so use a real tagged release when testing ingestion and never place
tokens in command arguments, committed files, or logs.

## Validate your change

```sh
go test ./...
go vet ./...
go build ./...
gofmt -l .
golangci-lint run ./...
go test $(go list ./... | grep -v '/cmd/') -count=1 -covermode=atomic -coverprofile=coverage.out
./scripts/check-coverage.sh coverage.out
python3 scripts/validate-manifest.py manifest.json
```

CI runs golangci-lint v2.14.0, enforces a 95% statement coverage floor
(`scripts/check-coverage.sh`), and checks that `manifest.json` parses and that
every download URL is a well-formed release-asset URL for the entry's own
repository and version tag. The last four commands reproduce those checks.
`validate-manifest.py` makes no network requests, so it cannot tell whether a
release actually exists.

`gofmt -l .` should print nothing. If it reports unrelated pre-existing drift,
none of the Go files touched by your change may appear in the output; do not add
to the output, and report what remains. For catalog output changes, inspect the
complete `manifest.json` diff and verify repository URLs, versions, platforms,
the checksum URL, capabilities, and presentation metadata against the source
release. The catalog stores a URL for `checksums.txt`, not the checksum values
themselves, so also confirm that the release asset exists and covers every
published binary.

## Open the pull request

Use a Conventional Commit title, explain the catalog or automation impact, and
paste the actual validation results. Read the
[AI-assisted contribution policy](https://github.com/prairie-server/prairie-server/blob/main/docs/ai-contributions.md)
and include its disclosure block.
