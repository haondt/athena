ATHENA_IMAGE="athena-test-image"
FLASK_IMAGE="flask-test-image"

ROOT_DIR=$(git rev-parse --show-toplevel)

docker build -t $ATHENA_IMAGE $ROOT_DIR -f $ROOT_DIR/tests/e2e/athena.dockerfile
docker build -t $FLASK_IMAGE $ROOT_DIR -f $ROOT_DIR/tests/e2e/flask.dockerfile
