repositories {
    maven("https://repo.papermc.io/repository/maven-public/")
}
dependencies {
    compileOnly("io.papermc.paper:paper-api:1.21.1-R0.1-SNAPSHOT")
}
tasks.jar {
    archiveFileName.set("MCOpsPlugin-Paper.jar")
}
