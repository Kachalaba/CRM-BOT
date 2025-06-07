# Developer Notes

This repository contains a Telegram bot built with `aiogram`. Below are some tips for working with the project.

## Running locally

1. Create a `.env` file based on `.env.example` and fill in the environment variables.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the bot:
   ```bash
   python main.py
   ```

Logs are written to `logs/bot.log` (rotating at 5 MB, 3 backups).

## Adding a new command

All bot handlers are defined in `handlers.py`. To add a new command:

1. Import any required modules at the top of `handlers.py`.
2. Add an async function decorated with `@dp.message(Command(commands=["<command>"]))`.
3. Implement the command logic inside this function.
4. Add a docstring explaining what the command does.

Run tests and format the code before committing.

## Tests location

Unit tests live under the `tests/` directory.
Run them with:
```bash
pytest -q
```

## Checklist before opening a PR

1. `pip install -r requirements.txt`
2. `pytest -q` – ensure all tests pass
3. `pre-commit run --all-files` (runs black, isort and flake8)
4. Follow commit message style `<scope>: <action>`
5. Push to a branch named `codex/<feature>-<date>`

