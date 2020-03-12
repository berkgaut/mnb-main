set IMAGE_VERSION=0.1

docker run --env DOCKER_HOST=tcp://host.docker.internal:2375 -v %CD%:/mnb/run --rm bberkgaut/mnb:%IMAGE_VERSION% python3 mnb-plan.py --windows-host --rootabspath %CD% %1 %2 %3 %4 %5 %6 %7 %8 %9