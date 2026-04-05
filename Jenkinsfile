pipeline {
    agent any

    environment {
        // 定义变量，方便修改
        // 注意：这里填你 GitHub 的用户名/仓库名
        DOCKER_IMAGE = 'lynnirist-lang/crawler-jenkins' 
        DOCKER_TAG = 'latest'
    }

    stages {
        // 阶段 1: 拉取代码
        stage('Checkout') {
            steps {
                echo '🚀 正在从 GitHub 拉取最新代码...'
                // 这里会自动使用你在 Jenkins 任务里配置的 Git 地址
                checkout scm
            }
        }

        // 阶段 2: 构建 Docker 镜像
        stage('Build Docker Image') {
            steps {
                echo '🔨 正在构建 Docker 镜像...'
                // 使用 Dockerfile 构建镜像，并打上标签
                sh """
                    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                """
            }
        }

        // 阶段 3: 运行容器进行测试
        stage('Run Container') {
            steps {
                echo '🐳 正在启动容器进行冒烟测试...'
                // 启动容器，后台运行，映射端口（假设你的程序用 8080，根据实际情况改）
                // --name 指定容器名，方便后续删除
                sh """
                    docker run -d --name test-container -p 8080:8080 ${DOCKER_IMAGE}:${DOCKER_TAG}
                """
            }
        }

        // 阶段 4: 验证服务是否存活 (冒烟测试)
        stage('Verify Service') {
            steps {
                echo '🔍 正在检查服务是否正常运行...'
                // 等待 5 秒让服务启动
                sh 'sleep 5'
                // 检查容器是否还在运行 (如果容器启动报错，它会立刻退出)
                sh """
                    if [ "\$(docker inspect -f '{{.State.Running}}' test-container)" == "true" ]; then
                        echo "✅ 容器运行正常！"
                    else
                        echo "❌ 容器启动失败，查看日志："
                        docker logs test-container
                        error "构建失败：容器未能保持运行状态"
                    fi
                """
            }
        }
    }

    // 无论成功失败，最后都要执行的清理工作
    post {
        always {
            echo '🧹 正在清理环境...'
            // 停止并删除测试容器
            sh '''
                docker stop test-container || true
                docker rm test-container || true
            '''
        }
    }
}
