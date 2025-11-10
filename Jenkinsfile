pipeline {
    agent any

    environment {
        // GitHub Container Registry settings
        GHCR_REGISTRY = 'ghcr.io'
        GITHUB_USERNAME = 'andersjinentri'  // Change to lowercase GitHub username
        IMAGE_NAME = 'pvbattery-api'
        FULL_IMAGE_NAME = "${GHCR_REGISTRY}/${GITHUB_USERNAME}/${IMAGE_NAME}"
        IMAGE_TAG = "${env.BUILD_NUMBER}"

        // Azure Container Apps settings
        RESOURCE_GROUP = 'rg-inentriq-aca'
        CONTAINER_APP_NAME = 'pvbattery-api'
        CONTAINER_APP_ENV = 'inentriq-env'
        AZURE_LOCATION = 'swedencentral'

        // Credentials stored in Jenkins
        AZURE_CREDENTIALS = credentials('azure-service-principal')
        AZURE_TENANT_ID = '85bd1e6b-a996-46bc-92c8-eb24dc3916fc'
        GITHUB_TOKEN = credentials('github-token')  // GitHub Personal Access Token
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
                    echo "Building Docker image: ${FULL_IMAGE_NAME}:${IMAGE_TAG}"
                    sh """
                        docker build -t ${FULL_IMAGE_NAME}:${IMAGE_TAG} .
                        docker tag ${FULL_IMAGE_NAME}:${IMAGE_TAG} ${FULL_IMAGE_NAME}:latest
                    """
                }
            }
        }

        stage('Login to GitHub Container Registry') {
            steps {
                script {
                    echo "Logging in to GitHub Container Registry..."
                    sh """
                        echo \$GITHUB_TOKEN | docker login ${GHCR_REGISTRY} -u ${GITHUB_USERNAME} --password-stdin
                    """
                }
            }
        }

        stage('Push to GitHub Container Registry') {
            steps {
                script {
                    echo "Pushing image to GHCR: ${FULL_IMAGE_NAME}:${IMAGE_TAG}"
                    sh """
                        docker push ${FULL_IMAGE_NAME}:${IMAGE_TAG}
                        docker push ${FULL_IMAGE_NAME}:latest
                    """
                }
            }
        }

        stage('Login to Azure') {
            steps {
                script {
                    echo "Logging in to Azure..."
                    sh """
                        az login --service-principal \\
                            -u \$AZURE_CREDENTIALS_USR \\
                            -p \$AZURE_CREDENTIALS_PSW \\
                            --tenant ${AZURE_TENANT_ID}
                    """
                }
            }
        }

        stage('Deploy to Azure Container Apps') {
            steps {
                script {
                    echo "Deploying to Azure Container Apps: ${CONTAINER_APP_NAME}"
                    sh """
                        # Check if container app exists
                        if ! az containerapp show --name ${CONTAINER_APP_NAME} --resource-group ${RESOURCE_GROUP} &> /dev/null; then
                            echo "Container App does not exist. Creating..."
                            az containerapp create \\
                                --name ${CONTAINER_APP_NAME} \\
                                --resource-group ${RESOURCE_GROUP} \\
                                --environment ${CONTAINER_APP_ENV} \\
                                --image ${FULL_IMAGE_NAME}:${IMAGE_TAG} \\
                                --target-port 8000 \\
                                --ingress external \\
                                --registry-server ${GHCR_REGISTRY} \\
                                --registry-username ${GITHUB_USERNAME} \\
                                --registry-password \$GITHUB_TOKEN \\
                                --min-replicas 1 \\
                                --max-replicas 3
                        else
                            echo "Container App exists. Updating with new image..."
                            az containerapp update \\
                                --name ${CONTAINER_APP_NAME} \\
                                --resource-group ${RESOURCE_GROUP} \\
                                --image ${FULL_IMAGE_NAME}:${IMAGE_TAG}
                        fi
                    """
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                script {
                    echo "Verifying deployment..."
                    sh """
                        sleep 30
                        curl -f https://${CONTAINER_APP_NAME}.${AZURE_LOCATION}.azurecontainerapps.io/health || exit 1
                    """
                }
            }
        }
    }

    post {
        success {
            echo "Deployment successful!"
            echo "Image: ${FULL_IMAGE_NAME}:${IMAGE_TAG}"
            echo "GHCR URL: https://github.com/${GITHUB_USERNAME}/PVBattery/pkgs/container/${IMAGE_NAME}"
            echo "API URL: https://${CONTAINER_APP_NAME}.${AZURE_LOCATION}.azurecontainerapps.io"
        }
        failure {
            echo "Deployment failed! Check logs above for details."
        }
        always {
            script {
                sh """
                    docker logout ${GHCR_REGISTRY} || true
                    az logout || true
                """
            }
        }
    }
}
