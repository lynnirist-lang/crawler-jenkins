pipeline {
    agent any

    environment {
        // 定义共享目录，对应你 Docker 挂载的 /opt/share_data
        SHARED_DATA = "/share_data"
        // 定义当前工作空间
        WORKSPACE_DIR = "${WORKSPACE}"
    }

    stages {
        stage('检出代码') {
            steps {
                // 从 GitHub 拉取代码
                checkout scm
            }
        }
        stage('准备 Python 环境') {
            steps {
                script {
                    echo '正在配置国内镜像源并安装 Python3...'
                    sh '''
                        # 1. 将 Debian 软件源替换为清华大学的镜像源
                       sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources

                       # 2. 更新软件包列表 (现在会从清华源下载，速度飞快)
                       apt-get update

                       # 3. 安装 Python3 和 Pip (自动确认安装，无需手动输入 Y)
                       apt-get install -y python3 python3-pip
                    '''

                    echo '正在安装依赖库...'
                    // 2. 再安装你的依赖
                    sh '''
                        if [ -f "requirements.txt" ]; then
                            pip3 install -r requirements.txt
                        else
                            echo "requirements.txt 未找到"
                        fi
                    '''
                }
            }
        }
        stage('执行爬虫任务') {
            steps {
                script {
                    echo '开始执行微博爬虫...'

                    // 步骤 1: 获取热搜关键词
                    // 注意：确保 tools/get_weibo_hot_search.py 路径正确
                    sh '''
                        echo "步骤 1: 爬取热搜关键词"
                        python3 tools/get_weibo_hot_search.py
                    '''

                    // 步骤 2: 根据关键词爬取帖子
                    // 注意：这里假设 main.py 是你的入口，且配置已指向生成的关键词文件
                    sh '''
                        echo "步骤 2: 爬取帖子内容"
                        python3 main.py
                    '''

                    // 步骤 3: 获取发帖人信息
                    sh '''
                        echo "步骤 3: 获取发帖人信息"
                        python3 -m media_platform.weibo.fetch_poster_info
                    '''
                }
            }
        }

        stage('归档结果到共享目录') {
            steps {
                script {
                    echo '正在将结果保存到共享目录...'

                    // 创建以时间戳命名的子目录，防止文件覆盖
                    // 使用 Jenkins 的 BUILD_ID 作为文件夹名
                    sh """
                        TARGET_DIR=${SHARED_DATA}/weibo_data_\${BUILD_ID}
                        mkdir -p \${TARGET_DIR}

                        # 假设你的数据输出在 data 目录下，请根据实际输出路径调整
                        # 这里使用 cp -r 递归复制
                        if [ -d "data" ]; then
                            cp -r data/* \${TARGET_DIR}/
                        fi

                        # 如果有其他生成的文件，也一并复制
                        # cp *.json \${TARGET_DIR}/
                    """
                    echo "数据已保存至宿主机目录: /opt/share_data/weibo_data_${env.BUILD_ID}"
                }
            }
        }
    }

    post {
        success {
            echo '🎉 爬虫任务执行成功！请检查宿主机的 /opt/share_data 目录。'
        }
        failure {
            echo '❌ 任务执行失败，请查看控制台输出排查错误。'
        }
    }
}
