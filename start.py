import sys

sys.dont_write_bytecode = True

import app as project_app


def main():
    """Start the Flask app without generating Python cache files."""
    if project_app.DB_KEEPER is None:
        project_app.DB_KEEPER = project_app.init_db(project_app.DATABASE_PATH)
        project_app.seed_defaults()
    project_app.UPLOAD_DIR.mkdir(exist_ok=True)
    project_app.app.run(debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
