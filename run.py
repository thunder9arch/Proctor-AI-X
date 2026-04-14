import sys

sys.dont_write_bytecode = True

import app as proctor_app


def main():
    """Start the Flask app without generating Python cache files."""
    if proctor_app.DB_KEEPER is None:
        proctor_app.DB_KEEPER = proctor_app.init_db(proctor_app.DATABASE_PATH)
        proctor_app.seed_defaults()
    proctor_app.UPLOAD_DIR.mkdir(exist_ok=True)
    proctor_app.app.run(debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
