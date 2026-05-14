plugins {
    id("java")
}
allprojects {
    group = "de.mcops"
    version = "1.0.0"
}
subprojects {
    apply(plugin = "java")
    java {
        toolchain.languageVersion.set(JavaLanguageVersion.of(21))
    }
    repositories {
        mavenCentral()
    }
    tasks.withType<JavaCompile> {
        options.encoding = "UTF-8"
        options.release.set(21)
    }
}
