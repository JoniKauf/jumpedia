USE jumpedia;

# SET foreign_key_checks = 0;
SET foreign_key_checks = 1;

CREATE TABLE IF NOT EXISTS location (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS location_alias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alias VARCHAR(100) UNIQUE NOT NULL,
    location_id INT NOT NULL,  
    FOREIGN KEY (location_id) REFERENCES location (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS location_parent (
    location_id INT NOT NULL,
    parent_id INT NOT NULL,
    PRIMARY KEY (location_id, parent_id),
    FOREIGN KEY (location_id) REFERENCES location (id) ON DELETE RESTRICT,
    FOREIGN KEY (parent_id) REFERENCES location (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS tier (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(16) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS difficulty (
	id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(16) UNIQUE NOT NULL,
    tier_id INT,
    FOREIGN KEY (tier_id) REFERENCES tier (id)
);

CREATE TABLE IF NOT EXISTS difficulty_alias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    difficulty_id INT NOT NULL,
    alias VARCHAR(16) UNIQUE NOT NULL,
    FOREIGN KEY (difficulty_id) REFERENCES difficulty (id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS type (
	id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(32),
    description VARCHAR(512)
);


CREATE TABLE IF NOT EXISTS person (
	id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS server (
	id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(32) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS server_alias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alias VARCHAR(100) UNIQUE NOT NULL,
    server_id INT NOT NULL,  
    FOREIGN KEY (server_id) REFERENCES server (id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS link (
	id INT AUTO_INCREMENT PRIMARY KEY,
    link VARCHAR(512) UNIQUE NOT NULL,
    description VARCHAR(255),
    author INT NULL,
    FOREIGN KEY (author) REFERENCES person (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS extra (
	id INT AUTO_INCREMENT PRIMARY KEY,
    text VARCHAR(1024) UNIQUE NOT NULL COLLATE utf8mb4_general1400_as_ci
);


CREATE TABLE IF NOT EXISTS tag (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tag VARCHAR(32) UNIQUE NOT NULL COLLATE utf8mb4_general1400_as_ci
);

CREATE TABLE IF NOT EXISTS thumbnail (
	id INT AUTO_INCREMENT PRIMARY KEY,
    link VARCHAR(512) UNIQUE NOT NULL
);


CREATE TABLE IF NOT EXISTS `rank` (
	power INT PRIMARY KEY,
    name VARCHAR(16)
);

# A user is an actual Jumpedia user while a
# person could be any finder, taser, prover ...
# A person must exist for a user to be defined
CREATE TABLE IF NOT EXISTS user (
    id BIGINT PRIMARY KEY,
    custom_name VARCHAR(64) NOT NULL,
    person_id INT NOT NULL,
    rank_power INT NOT NULL DEFAULT 0,
    FOREIGN KEY (person_id) REFERENCES person (id),
    FOREIGN KEY (rank_power) REFERENCES `rank` (power)
);



CREATE TABLE IF NOT EXISTS trickjump (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) UNIQUE NOT NULL COLLATE utf8mb4_general1400_as_ci,
    location_id INT NOT NULL,
    difficulty_id INT NOT NULL,
    type_id INT NOT NULL,
    found_at DATETIME NULL,
    tased_at DATETIME NULL,
    proven_at DATETIME NULL,
    server_id INT NOT NULL,
    thumbnail_id INT,
    FOREIGN KEY (location_id) REFERENCES location (id) ON DELETE RESTRICT,
    FOREIGN KEY (difficulty_id) REFERENCES difficulty (id) ON DELETE RESTRICT,
    FOREIGN KEY (type_id) REFERENCES type (id) ON DELETE RESTRICT,
    FOREIGN KEY (server_id) REFERENCES server (id) ON DELETE RESTRICT,
    FOREIGN KEY (thumbnail_id) REFERENCES thumbnail (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS user_trickjump (
    trickjump_id INT NOT NULL,
    user_id BIGINT NOT NULL,
    proof VARCHAR(512),
    given_at DATETIME,
    PRIMARY KEY (trickjump_id, user_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS trickjump_finder (
    trickjump_id INT NOT NULL,
    person_id INT NOT NULL,
    PRIMARY KEY (trickjump_id, person_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES person (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS trickjump_taser (
    trickjump_id INT NOT NULL,
    person_id INT NOT NULL,
    PRIMARY KEY (trickjump_id, person_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES person (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS trickjump_prover (
    trickjump_id INT NOT NULL,
    person_id INT NOT NULL,
    PRIMARY KEY (trickjump_id, person_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES person (id) ON DELETE RESTRICT
);



CREATE TABLE IF NOT EXISTS trickjump_extra (
	trickjump_id INT NOT NULL,
    extra_id INT NOT NULL,
    PRIMARY KEY (trickjump_id, extra_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (extra_id) REFERENCES extra (id) ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS trickjump_tag (
    trickjump_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (trickjump_id, tag_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tag (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS trickjump_link (
    trickjump_id INT NOT NULL,
    link_id INT NOT NULL,
    PRIMARY KEY (trickjump_id, link_id),
    FOREIGN KEY (trickjump_id) REFERENCES trickjump (id) ON DELETE CASCADE,
    FOREIGN KEY (link_id) REFERENCES link (id) ON DELETE RESTRICT
);