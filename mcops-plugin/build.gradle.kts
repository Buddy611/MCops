plugins {
    id("java")
}

group = "de.mcops"
version = "1.0.0"
description = "MCOps Panel Integration Plugin"

java {
    toolchain.languageVersion.set(JavaLanguageVersion.of(21))
}

repositories {
    mavenCentral()
    maven("https://repo.papermc.io/repository/maven-public/")
}

dependencies {
    // Paper API – compile only (provided by the server at runtime)
    compileOnly("io.papermc.paper:paper-api:1.21.1-R0.1-SNAPSHOT")
}

tasks.jar {
    // Include plugin.yml and config.yml from resources
    from(sourceSets.main.get().resources)

    archiveFileName.set("MCOpsPlugin-${version}.jar")

    manifest {
        attributes["Implementation-Title"]   = "MCOpsPlugin"
        attributes["Implementation-Version"] = version
    }
}

tasks.withType<JavaCompile> {
    options.encoding = "UTF-8"
    options.release.set(21)
}
