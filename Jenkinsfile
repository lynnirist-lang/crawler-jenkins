pipeline {
    agent any

    environment {
        // 定义共享目录，对应你宿主机挂载的 /opt/share_data
        SHARED_DATA = "/share_data"
        // 定义镜像名称
        IMAGE_NAME = "my-mediacrawler"
    }

    stages {
        stage('检出代码') {
            steps {
                // 从 GitHub 拉取代码
                checkout scm
            }
        }

        stage('构建 Docker 镜像') {
            steps {
                script {
                    echo '🔨 正在根据 Dockerfile 构建镜像 (包含 Python 3.11 和依赖)...'
                    // 这一步会读取你项目里的 Dockerfile
                    // 因为 Dockerfile 里已经装了依赖，所以这里构建完环境就准备好了
                    sh '''
                        docker build -t ${IMAGE_NAME} .
                    '''
                }
            }
        }

        stage('执行爬虫任务') {
            steps {
                script {
                    echo '🚀 正在启动临时容器执行爬虫...'
                    
                    // 使用 docker run 运行刚才构建的镜像
                    // --rm: 运行完自动删除容器
                    // -v: 挂载共享目录，让数据能保存到宿主机
                    sh """
                        docker run --rm \
                            -v ${SHARED_DATA}:${SHARED_DATA} \
                            ${IMAGE_NAME} python3 tools/get_weibo_hot_search.py
                            
                        docker run --rm \
                            -v ${SHARED_DATA}:${SHARED_DATA} \
                            ${IMAGE_NAME} python3 main.py
                            
                        docker run --rm \
                            -v ${SHARED_DATA}:${SHARED_DATA} \
                            ${IMAGE_NAME} python3 -m media_platform.weibo.fetch_poster_info
                    """
                }
            }
        }

        stage('归档结果到共享目录') {
            steps {
                script {
                    echo '✅ 任务完成，数据已保存在共享目录中。'
                    // 因为我们在上面 docker run 时挂载了共享目录
                    // 爬虫产生的数据应该已经在 /opt/share_data 下了
                    // 这里不需要 cp 命令了，因为容器里产生的数据直接就在宿主机目录里
                }
            }
        }
    }

    post {
        success {
            echo '🎉 爬虫任务执行成功！请检查宿主机的 ${SHARED_DATA} 目录。'
        }
        failure {
            echo '❌ 任务执行失败，请查看控制台输出排查错误。'
        }
    }
}
