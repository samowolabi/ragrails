# CLI Doctor

`ragrails doctor` checks the local project setup before you run SDK-backed CLI
commands in development or production.

## Commands

```bash
ragrails doctor
```

Checks:

- `.ragrails.toml` exists and can be parsed.
- Required sections are present.
- Configured providers are supported by the CLI.
- Required config values are present.
- Provider packages can be imported.
- Required environment variables are set.

The default command does not call external services.

```bash
ragrails doctor --connections
```

Also checks vector database reachability where supported. Qdrant and Qdrant
Cloud are checked with a bounded request to `/collections`.

```bash
ragrails doctor --json
```

Prints machine-readable output for CI or scripts.

Use `--config path/to/.ragrails.toml` to inspect a config file outside the
current working directory.
