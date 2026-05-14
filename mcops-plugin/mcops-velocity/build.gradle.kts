repositories {
    maven("https://repo.papermc.io/repository/maven-public/")
}
dependencies {
    compileOnly("com.velocitypowered:velocity-api:3.3.0-SNAPSHOT")
    annotationProcessor("com.velocitypowered:velocity-api:3.3.0-SNAPSHOT")
}
tasks.jar {
    archiveFileName.set("MCOpsPlugin-Velocity.jar")
}
