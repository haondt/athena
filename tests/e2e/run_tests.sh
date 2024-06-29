ATHENA_IMAGE="athena-test-image"
FLASK_IMAGE="flask-test-image"

ROOT_DIR=$(git rev-parse --show-toplevel)

echo "starting api server..."
docker network create -d bridge athena
docker run --rm -d -p 5000:5000 -v $ROOT_DIR/tests/e2e/server.py:/app/server.py --name $FLASK_IMAGE --net=athena --net-alias=$FLASK_IMAGE $FLASK_IMAGE server.py
sleep 0.25
echo "running tests..."
docker run --rm -v $ROOT_DIR/tests/e2e:/tests --name $ATHENA_IMAGE --net=athena $ATHENA_IMAGE -vv
echo "cleaning up docker resources..."
docker stop $FLASK_IMAGE
docker network rm athena
