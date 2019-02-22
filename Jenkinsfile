#!/usr/bin/env groovy

@Library("jenkinstools@18.9.4") _

withSplunkWrapNode("master") {
    def buildImage = "repo.splunk.com/splunk/app-build:1.0"
    def branchName = env.BRANCH_NAME
    def defaultPublish = false
    if(branchName == "master" || branchName == "develop"){
        // only master and develop will build and publish python package by default
        defaultPublish = true
    }

    properties([
        disableConcurrentBuilds(),
        parameters([
            booleanParam(defaultValue: defaultPublish, description: 'Build new package and publish to repo.',name: 'PUBLISH'),
            string(defaultValue: "", description: 'Customize the postfix if needed. The version would be {version_number}.{version_postfix}', name: 'version_postfix'),
        ])
    ])

    def PUBLISH = params.PUBLISH
    def version_postfix = params.version_postfix
    def jobs = [:]
    if (branchName == "develop") {
        stage("Publish Document") {
            withCredentials([file(credentialsId: 'app_common_publish_doc_key', variable: 'FILE')]) {
                splunkPrepareAndCheckOut imageName: buildImage,
                                    repoName: env.GIT_SSH_URL,
                                    files: "$FILE",
                                    branchName: branchName;
            }

            splunkRunScript imageName: buildImage,
                            script: """
                                npm install --unsafe-perm;
                                pip install Sphinx;
                                npm run docs;
                                mkdir doc;
                                mv docs/_build/html/* doc/;
                                chmod 400 /build/app_common_publish_doc_key
                                scp -C -o StrictHostKeyChecking=no -i /build/app_common_publish_doc_key -r doc/* bamboo@sc-build.sv.splunk.com:/usr/local/bamboo/releases/app_shared_components/lib-solutions-python
                             """
        }
    }
    try {
        stage("Test") {
            splunkPrepareAndCheckOut imageName: buildImage,
                        repoName: env.GIT_SSH_URL,
                        branchName: branchName;

            splunkRunScript imageName: buildImage,
                            script: "sh tests/run_test.sh"
        }

        if (Boolean.valueOf(PUBLISH)) {
            if(version_postfix == ""){
                if (branchName == "master"){
                    version_postfix = ""
                } else if (branchName == "develop"){
                    version_postfix = "--postfix " +"dev.${env.BUILD_ID}"
                } else {
                    version_postfix = "--postfix " +"${branchName}.${env.BUILD_ID}".replaceAll('/','.')
                }
            } else {
                version_postfix = "--postfix " + version_postfix.replaceAll('/','.')
            }

            stage("Check Version") {
                splunkPrepareAndCheckOut imageName: buildImage,
                                    repoName: env.GIT_SSH_URL,
                                    branchName: branchName;

                splunkRunScript imageName: buildImage,
                                script: "sh tests/before_publish.sh ${version_postfix}"

                splunkCopyFromDocker files: "upload_check.json",
                                    persistOriginal: false,
                                    remotePath: "/build/lib-solutions-python"
                def props = readJSON file: "target/upload_check.json"
                exist = props['exists']
                version = props['version']
            }
            if (exist) {
                ansiColor("xterm") {
                    echo "\033[43m This version already exist on Repo. Please update the version or delete the deprecated one. \033[0m"
                }
            } else {
                stage("Build & Publish"){
                    splunkBuildApp imageName: buildImage,
                                    runner  : "npm";

                    splunkPublishPython  imageName  : buildImage,
                                    buildDir        :"${env.GIT_SSH_URL}/build",
                                    repository      :"pypi-solutions-local";

                    if (branchName == 'master') {
                        splunkRunScript imageName: buildImage,
                            script: """
                                git tag ${version};
                                git push --tags;
                            """;

                            ansiColor("xterm") {
                                echo "\033[42m Publish docs and tagged with version ${version} ! \033[0m"
                            }
                    } 
                }
            }

        }
    }
    catch (Exception e) {
        echo "Exception Caught: ${e.getMessage()}"
        currentBuild.result = 'FAILURE'
    }
}