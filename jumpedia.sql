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



INSERT INTO tier (name) VALUES
('Practice Tier'),
('Beginner'),
('Intermediate'),
('Advanced'),
('Expert'),
('Master'),
('Low Elite'),
('Mid Elite'),
('High Elite'),
('Insanity Elite'),
('God Tier'),
('Hell Tier'),
('Unproven');

INSERT INTO difficulty (name, tier_id) VALUES
('0/10', (SELECT id FROM tier WHERE name = 'Practice Tier')),
('0.5/10', (SELECT id FROM tier WHERE name = 'Beginner')),
('1/10', (SELECT id FROM tier WHERE name = 'Beginner')),
('1.5/10', (SELECT id FROM tier WHERE name = 'Beginner')),
('2/10', (SELECT id FROM tier WHERE name = 'Beginner')),
('2.5/10', (SELECT id FROM tier WHERE name = 'Beginner')),
('3/10', (SELECT id FROM tier WHERE name = 'Beginner')),
('3.5/10', (SELECT id FROM tier WHERE name = 'Intermediate')),
('4/10', (SELECT id FROM tier WHERE name = 'Intermediate')),
('4.5/10', (SELECT id FROM tier WHERE name = 'Intermediate')),
('5/10', (SELECT id FROM tier WHERE name = 'Intermediate')),
('5.5/10', (SELECT id FROM tier WHERE name = 'Advanced')),
('6/10', (SELECT id FROM tier WHERE name = 'Advanced')),
('6.5/10', (SELECT id FROM tier WHERE name = 'Advanced')),
('7/10', (SELECT id FROM tier WHERE name = 'Expert')),
('7.5/10', (SELECT id FROM tier WHERE name = 'Expert')),
('8/10', (SELECT id FROM tier WHERE name = 'Expert')),
('8.5/10', (SELECT id FROM tier WHERE name = 'Master')),
('9/10', (SELECT id FROM tier WHERE name = 'Master')),
('9.5/10', (SELECT id FROM tier WHERE name = 'Master')),
('10/10', (SELECT id FROM tier WHERE name = 'Master')),
('Low Elite', (SELECT id FROM tier WHERE name = 'Low Elite')),
('Mid Elite', (SELECT id FROM tier WHERE name = 'Mid Elite')),
('High Elite', (SELECT id FROM tier WHERE name = 'High Elite')),
('Insanity Elite', (SELECT id FROM tier WHERE name = 'Insanity Elite')),
('God Tier', (SELECT id FROM tier WHERE name = 'God Tier')),
('Hell Tier', (SELECT id FROM tier WHERE name = 'Hell Tier')),
('Unproven', (SELECT id FROM tier WHERE name = 'Unproven'));


INSERT INTO location (name) VALUES
('Cap Kingdom'),
('Cascade Kingdom'),
('Sand Kingdom'),
('Lake Kingdom'),
('Wooded Kingdom'),
('Cloud Kingdom'),
('Lost Kingdom'),
('Metro Kingdom'),
('Snow Kingdom'),
('Seaside Kingdom'),
('Luncheon Kingdom'),
('Ruined Kingdom'),
('Bowser''s Kingdom'),
('Moon Kingdom'),
('Mushroom Kingdom'),
('Dark Side'),
('Darker Side');


INSERT INTO location_alias (alias, location_id) VALUES
('Cap', (SELECT id FROM location WHERE name = 'Cap Kingdom')),
('Cascade', (SELECT id FROM location WHERE name = 'Cascade Kingdom')),
('Sand', (SELECT id FROM location WHERE name = 'Sand Kingdom')),
('Lake', (SELECT id FROM location WHERE name = 'Lake Kingdom')),
('Wooded', (SELECT id FROM location WHERE name = 'Wooded Kingdom')),
('Cloud', (SELECT id FROM location WHERE name = 'Cloud Kingdom')),
('Lost', (SELECT id FROM location WHERE name = 'Lost Kingdom')),
('Metro', (SELECT id FROM location WHERE name = 'Metro Kingdom')),
('Snow', (SELECT id FROM location WHERE name = 'Snow Kingdom')),
('Seaside', (SELECT id FROM location WHERE name = 'Seaside Kingdom')),
('Luncheon', (SELECT id FROM location WHERE name = 'Luncheon Kingdom')),
('Ruined', (SELECT id FROM location WHERE name = 'Ruined Kingdom')),
('Bowser', (SELECT id FROM location WHERE name = 'Bowser''s Kingdom')),
('Bowsers', (SELECT id FROM location WHERE name = 'Bowser''s Kingdom')),
('Bowser''s', (SELECT id FROM location WHERE name = 'Bowser''s Kingdom')),
('Bowser Kingdom', (SELECT id FROM location WHERE name = 'Bowser''s Kingdom')),
('Bowsers Kingdom', (SELECT id FROM location WHERE name = 'Bowser''s Kingdom')),
('Moon', (SELECT id FROM location WHERE name = 'Moon Kingdom')),
('Mushroom', (SELECT id FROM location WHERE name = 'Mushroom Kingdom')),
('Dark', (SELECT id FROM location WHERE name = 'Dark Side')),
('Darker', (SELECT id FROM location WHERE name = 'Darker Side'));

