pipeline {
    agent any

    environment {
        // Docker image settings
        IMAGE_NAME = 'pvbattery-api'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        DOCKER_TAR = "pvbattery-api-${env.BUILD_NUMBER}.tar"

        // Azure Container Apps settings
        RESOURCE_GROUP = 'rg-inentriq-aca'
        CONTAINER_APP_NAME = 'pvbattery-api'
        CONTAINER_APP_ENV = 'inentriq-env'
        AZURE_LOCATION = 'swedencentral'

        // Credentials stored in Jenkins
        AZURE_CREDENTIALS = credentials('azure-service-principal')
        AZURE_TENANT_ID = '85bd1e6b-a996-46bc-92c8-eb24dc3916fc'
    }

    // Only build azure-api branch
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                echo "Checking out branch: ${env.BRANCH_NAME}"
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    echo "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"
                    bat """
                        docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest
                    """
                }
            }
        }

        stage('Save Docker Image') {
            steps {
                script {
                    echo "Saving Docker image to tar file: ${DOCKER_TAR}"
                    bat """
                        docker save ${IMAGE_NAME}:${IMAGE_TAG} -o ${DOCKER_TAR}
                    """
                }
            }
        }

        stage('Login to Azure') {
            steps {
                script {
                    echo "Logging in to Azure..."
                    bat """
                        az login --service-principal ^
                            -u %AZURE_CREDENTIALS_USR% ^
                            -p %AZURE_CREDENTIALS_PSW% ^
                            --tenant ${AZURE_TENANT_ID}
                    """
                }
            }
        }

        stage('Deploy to Azure Container Apps') {
            steps {
                script {
                    echo "Deploying to Azure Container Apps: ${CONTAINER_APP_NAME}"
                    bat """
                        az containerapp up ^
                            --name ${CONTAINER_APP_NAME} ^
                            --resource-group ${RESOURCE_GROUP} ^
                            --environment ${CONTAINER_APP_ENV} ^
                            --image ${IMAGE_NAME}:${IMAGE_TAG} ^
                            --source ${DOCKER_TAR} ^
                            --target-port 8000 ^
                            --ingress external
                    """
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                script {
                    echo "Verifying deployment..."
                    bat """
                        timeout /t 30 /nobreak
                        curl -f https://${CONTAINER_APP_NAME}.azurecontainerapps.io/health || exit 1
                    """
                }
            }
        }
    }

    post {
        success {
            echo "Deployment successful! Image: ${IMAGE_NAME}:${IMAGE_TAG}"
            echo "Access your API at: https://${CONTAINER_APP_NAME}.${AZURE_LOCATION}.azurecontainerapps.io"
        }
        failure {
            echo "Deployment failed! Check logs above for details."
        }
        always {
            script {
                bat """
                    if exist ${DOCKER_TAR} del ${DOCKER_TAR}
                    az logout
                """
            }
        }
    }
}
